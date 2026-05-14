"""Video endpoints — upload, detail, and listing."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.video import (
    FrameAnalysisResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoUploadResponse,
)
from app.services import video_service

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoUploadResponse, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await video_service.upload_video(
        db,
        current_user=current_user,
        file=file,
        latitude=latitude,
        longitude=longitude,
    )


@router.post("/analyze-frame", response_model=FrameAnalysisResponse)
async def analyze_frame(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await video_service.analyze_frame(file)


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await video_service.delete_video(db, current_user, video_id)


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await video_service.get_video(db, video_id)


@router.get("", response_model=VideoListResponse)
async def list_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await video_service.list_videos(db, current_user, skip=skip, limit=limit)
