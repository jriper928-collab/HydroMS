"""SQLAlchemy model for farmer user accounts."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(256), default=None)
    full_name: Mapped[str] = mapped_column(String(200))
    google_id: Mapped[str | None] = mapped_column(String(100), unique=True, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    videos = relationship("Video", back_populates="farmer")
