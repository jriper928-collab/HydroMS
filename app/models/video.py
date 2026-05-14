"""SQLAlchemy model for uploaded / processed videos with status tracking."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin
from app.models.user import User  # noqa: F401 — ensure relationship target is registered


class VideoStatus(str, enum.Enum):
    PENDING = "PENDING"
    STABILIZING = "STABILIZING"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    GENERATING_METADATA = "GENERATING_METADATA"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class Video(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "videos"

    farmer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus), default=VideoStatus.PENDING
    )
    raw_path: Mapped[str | None] = mapped_column(String(500), default=None)
    processed_path: Mapped[str | None] = mapped_column(String(500), default=None)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), default=None)

    # LLM generated metadata
    title_az: Mapped[str | None] = mapped_column(Text, default=None)
    title_en: Mapped[str | None] = mapped_column(Text, default=None)
    title_ar: Mapped[str | None] = mapped_column(Text, default=None)
    hashtags_az: Mapped[str | None] = mapped_column(Text, default=None)
    hashtags_en: Mapped[str | None] = mapped_column(Text, default=None)
    hashtags_ar: Mapped[str | None] = mapped_column(Text, default=None)

    # Instagram publish result
    instagram_media_id: Mapped[str | None] = mapped_column(String(100), default=None)
    instagram_permalink: Mapped[str | None] = mapped_column(String(500), default=None)

    # GPS coordinates at upload time
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)

    # Status transition timestamps
    stabilized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    audio_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    metadata_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    farmer = relationship("User", back_populates="videos")
    location = relationship("Location", back_populates="video", uselist=False, cascade="all, delete-orphan")
