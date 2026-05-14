"""Async pipeline orchestrator — runs all processing steps sequentially
with a fresh DB session per step to avoid holding locks across API calls."""

from datetime import datetime, timezone

import cv2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.video import Video, VideoStatus
from app.pipeline.audio_processing import process_audio
from app.pipeline.instagram_publish import publish_to_instagram
from app.pipeline.metadata_generation import generate_metadata
from app.pipeline.stabilization import stabilize_video


def _save_thumbnail(video_path: str, video_id: str) -> str | None:
    """Extract middle frame from video or copy image and save as JPEG thumbnail."""
    from pathlib import Path
    ext = Path(video_path).suffix.lower()
    thumb_path = settings.MEDIA_PROCESSED_DIR / f"{video_id}_thumb.jpg"

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        frame = cv2.imread(video_path)
    else:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return None

    if frame is None:
        return None
    cv2.imwrite(str(thumb_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(thumb_path)


async def _update_status(
    db: AsyncSession, video_id: str, status: VideoStatus, **extra
) -> None:
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return
    video.status = status
    for key, value in extra.items():
        setattr(video, key, value)
    await db.commit()


async def _with_session(video_id: str, status: VideoStatus, **extra) -> None:
    async with AsyncSessionLocal() as db:
        await _update_status(db, video_id, status, **extra)


async def run_pipeline(video_id: str, farmer_id: str) -> None:
    try:
        logger.info("pipeline_started", video_id=video_id)

        # Step 1 — Stabilization (manages its own DB session internally)
        async with AsyncSessionLocal() as db:
            stabilized_path = await stabilize_video(video_id, db)
        logger.info("pipeline_step_complete", video_id=video_id, step="stabilization")

        # Step 2 — Audio processing
        await _with_session(video_id, VideoStatus.AUDIO_PROCESSING)
        audio_path = await process_audio(stabilized_path)

        # Generate thumbnail from the processed video
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        thumb_path = await loop.run_in_executor(None, _save_thumbnail, audio_path, video_id)

        await _with_session(
            video_id, VideoStatus.AUDIO_PROCESSING,
            processed_path=audio_path,
            thumbnail_path=thumb_path,
            audio_processed_at=datetime.now(timezone.utc),
        )
        logger.info("pipeline_step_complete", video_id=video_id, step="audio_processing")

        # Step 3 — Metadata generation
        await _with_session(video_id, VideoStatus.GENERATING_METADATA)
        metadata = await generate_metadata(video_id)
        await _with_session(
            video_id, VideoStatus.GENERATING_METADATA,
            title_az=metadata["title_az"],
            title_en=metadata["title_en"],
            title_ar=metadata["title_ar"],
            hashtags_az=metadata["hashtags_az"],
            hashtags_en=metadata["hashtags_en"],
            hashtags_ar=metadata["hashtags_ar"],
            metadata_generated_at=datetime.now(timezone.utc),
        )
        logger.info("pipeline_step_complete", video_id=video_id, step="metadata_generation")

        # Step 4 — Instagram publish
        await _with_session(video_id, VideoStatus.PUBLISHING)
        permalink = await publish_to_instagram(
            video_id, metadata["title_en"], metadata["hashtags_en"], is_image=False
        )
        await _with_session(
            video_id, VideoStatus.PUBLISHED,
            instagram_permalink=permalink,
            published_at=datetime.now(timezone.utc),
        )
        logger.info("pipeline_completed", video_id=video_id)

    except Exception as exc:
        logger.error("pipeline_failed", video_id=video_id, error=str(exc))
        await _with_session(
            video_id, VideoStatus.FAILED,
            error_message=str(exc),
            failed_at=datetime.now(timezone.utc),
        )
        raise


async def run_image_pipeline(video_id: str, image_path: str) -> None:
    """Simplified pipeline for image uploads: thumbnail → metadata → publish."""
    try:
        logger.info("image_pipeline_started", video_id=video_id)

        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()

        # Thumbnail from image
        thumb_path = await loop.run_in_executor(None, _save_thumbnail, image_path, video_id)

        await _with_session(
            video_id, VideoStatus.GENERATING_METADATA,
            processed_path=image_path,
            thumbnail_path=thumb_path,
        )

        # Metadata from image (metadata_generation._extract_frame_b64 handles images)
        metadata = await generate_metadata(video_id, media_path_override=image_path)
        await _with_session(
            video_id, VideoStatus.GENERATING_METADATA,
            title_az=metadata["title_az"],
            title_en=metadata["title_en"],
            title_ar=metadata["title_ar"],
            hashtags_az=metadata["hashtags_az"],
            hashtags_en=metadata["hashtags_en"],
            hashtags_ar=metadata["hashtags_ar"],
            metadata_generated_at=datetime.now(timezone.utc),
        )
        logger.info("image_pipeline_step_complete", video_id=video_id, step="metadata")

        await _with_session(video_id, VideoStatus.PUBLISHING)
        permalink = await publish_to_instagram(
            video_id, metadata["title_en"], metadata["hashtags_en"], is_image=True
        )
        await _with_session(
            video_id, VideoStatus.PUBLISHED,
            instagram_permalink=permalink,
            published_at=datetime.now(timezone.utc),
        )
        logger.info("image_pipeline_completed", video_id=video_id)

    except Exception as exc:
        logger.error("image_pipeline_failed", video_id=video_id, error=str(exc))
        await _with_session(
            video_id, VideoStatus.FAILED,
            error_message=str(exc),
            failed_at=datetime.now(timezone.utc),
        )
        raise
