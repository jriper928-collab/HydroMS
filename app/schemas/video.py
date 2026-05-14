"""Pydantic schemas for video upload, detail, and list responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    id: str
    status: str
    message: str = "Video uploaded. Processing pipeline started."


class VideoDetailResponse(BaseModel):
    id: str
    status: str
    raw_path: str | None = None
    processed_path: str | None = None
    thumbnail_path: str | None = None
    title_en: str | None = None
    title_az: str | None = None
    title_ar: str | None = None
    hashtags_en: str | None = None
    hashtags_az: str | None = None
    hashtags_ar: str | None = None
    instagram_permalink: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    error_message: str | None = None
    stabilized_at: datetime | None = None
    audio_processed_at: datetime | None = None
    metadata_generated_at: datetime | None = None
    published_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class VideoListItem(BaseModel):
    id: str
    status: str
    title_en: str | None = None
    title_az: str | None = None
    thumbnail_path: str | None = None
    processed_path: str | None = None
    instagram_permalink: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoListResponse(BaseModel):
    items: list[VideoListItem]
    total: int


class FrameAnalysisResponse(BaseModel):
    tip: str
    frame_b64: str
