"""SQLAlchemy model for GPS locations pinned to published videos."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import UUIDMixin, generate_uuid
from app.models.user import User  # noqa: F401
from app.models.video import Video  # noqa: F401


class Location(Base, UUIDMixin):
    __tablename__ = "locations"

    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos.id"), unique=True, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    video = relationship("Video", back_populates="location")
