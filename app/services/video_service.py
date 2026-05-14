"""Video orchestration — upload, status, listing, and background pipeline launch."""

import asyncio
import base64
import os
import tempfile
import threading

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from openai import OpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.models.location import Location
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.pipeline.orchestrator import run_image_pipeline, run_pipeline
from app.schemas.video import (
    FrameAnalysisResponse,
    VideoDetailResponse,
    VideoListItem,
    VideoListResponse,
    VideoUploadResponse,
)
from app.services.storage_service import build_raw_filename, save_raw_video
from app.utils.file_utils import is_image_extension, validate_file_size, validate_media_file
from app.utils.gps import validate_coordinates

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

FRAME_ANALYSIS_SYSTEM_PROMPT = """Sən AgroVibe AZ üçün peşəkar kənd
təsərrüfatı video operatoru və vizual məsləhətçisisən.
Çiftçilərə telefonla daha gözəl, peşəkar görünüşlü çəkilişlər
etməyi öyrədirsən.
Tövsiyələrin qısa, praktik və Azərbaycan dilində olmalıdır.
Texniki jarqon işlətmə — sadə dil işlət."""

FRAME_ANALYSIS_USER_PROMPT = """Bu kənd təsərrüfatı çəkilişinə bax.
Çiftçiyə BU KADR üçün konkret 1 tövsiyə ver:
- Kameranı necə tutmalı (bucaq, hündürlük)
- İşıqlandırmanı necə yaxşılaşdırmaq olar
- Kadrda nəyi ön plana çıxarmaq lazımdır
Cavabı bu formatda ver:
\"[Konkret tövsiyə]. Beləliklə [nəticə] görünəcək.\"
Maksimum 2 cümlə. Yalnız Azərbaycan dilində."""


def _run_pipeline_in_thread(video_id: str, farmer_id: str) -> None:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_pipeline(video_id, farmer_id))
        loop.close()
    except Exception:
        logger.exception("pipeline_thread_failed", video_id=video_id)


def _run_image_pipeline_in_thread(video_id: str, image_path: str) -> None:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_image_pipeline(video_id, image_path))
        loop.close()
    except Exception:
        logger.exception("image_pipeline_thread_failed", video_id=video_id)


async def upload_video(
    db: AsyncSession,
    current_user: User,
    file,
    latitude: float | None,
    longitude: float | None,
) -> VideoUploadResponse:
    header = await file.read(12)
    await file.seek(0)
    validate_media_file(file.filename or "upload.bin", header)
    if file.size is not None:
        validate_file_size(file.size)
    if latitude is not None and longitude is not None:
        validate_coordinates(latitude, longitude)

    video = Video(
        farmer_id=current_user.id,
        status=VideoStatus.PENDING,
        raw_path="",
        latitude=latitude,
        longitude=longitude,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    filename = build_raw_filename(str(video.id), file.filename or "video.mp4")
    raw_path = await save_raw_video(file, filename)
    video.raw_path = raw_path

    if latitude is not None and longitude is not None:
        location = Location(
            video_id=video.id,
            latitude=latitude,
            longitude=longitude,
        )
        db.add(location)

    await db.commit()
    await db.refresh(video)

    is_image = is_image_extension(file.filename or "")
    if is_image:
        from app.config import settings as _s
        full_image_path = str(_s.MEDIA_RAW_DIR / filename)
        threading.Thread(
            target=_run_image_pipeline_in_thread,
            args=(str(video.id), full_image_path),
            daemon=True,
        ).start()
    else:
        threading.Thread(
            target=_run_pipeline_in_thread,
            args=(str(video.id), str(current_user.id)),
            daemon=True,
        ).start()

    return VideoUploadResponse(
        id=str(video.id),
        status=video.status.value,
        message="Video uploaded. Processing pipeline started.",
    )


async def get_video(db: AsyncSession, video_id: str) -> VideoDetailResponse:
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoDetailResponse.model_validate(video)


async def list_videos(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
) -> VideoListResponse:
    base = select(Video).where(Video.farmer_id == current_user.id).order_by(Video.created_at.desc())

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    items_result = await db.execute(base.offset(skip).limit(limit))
    items = items_result.scalars().all()

    return VideoListResponse(
        items=[VideoListItem.model_validate(v) for v in items],
        total=total,
    )


async def delete_video(
    db: AsyncSession,
    current_user: User,
    video_id: str,
) -> None:
    from sqlalchemy import delete as sa_delete
    from app.models.location import Location

    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.farmer_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.execute(sa_delete(Location).where(Location.video_id == video_id))
    await db.execute(sa_delete(Video).where(Video.id == video_id))
    await db.commit()


async def analyze_frame(file: UploadFile) -> FrameAnalysisResponse:
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in _IMAGE_EXTS | _VIDEO_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_type = "image" if ext in _IMAGE_EXTS else "video"
    logger.info("analyze_frame_start", filename=filename, type=file_type)

    file_bytes = await file.read()

    loop = asyncio.get_running_loop()

    def _extract_and_encode() -> str:
        if file_type == "image":
            nparr = np.frombuffer(file_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                cap = cv2.VideoCapture(tmp_path)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
                _, frame = cap.read()
                cap.release()
            finally:
                os.unlink(tmp_path)

        if frame is None:
            return ""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buf.tobytes()).decode()

    b64 = await loop.run_in_executor(None, _extract_and_encode)

    if not b64:
        raise HTTPException(status_code=400, detail="Could not extract frame from file")

    logger.info("analyze_frame_extracted", size_kb=round(len(file_bytes) / 1024, 1))

    if not settings.OPENROUTER_API_KEY:
        logger.info("analyze_frame_fallback")
        tip = (
            "Kameranı sabit tutun və yaxşı işıqlı yerdə çəkin. "
            "Beləliklə video daha peşəkar görünəcək."
        )
        return FrameAnalysisResponse(tip=tip, frame_b64=b64)

    def _call_openrouter() -> str:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": FRAME_ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": FRAME_ANALYSIS_USER_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                },
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    try:
        tip = await loop.run_in_executor(None, _call_openrouter)
    except Exception:
        raise HTTPException(status_code=502, detail="Frame analysis service unavailable")

    logger.info("analyze_frame_tip_generated")
    return FrameAnalysisResponse(tip=tip, frame_b64=b64)
