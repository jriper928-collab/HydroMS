"""Reusable SQLAlchemy mixins — UUID primary key and timestamp columns."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.orm import Mapped, mapped_column


def generate_uuid() -> str:
    return uuid.uuid4().hex


class UUIDMixin:
    id: Mapped[str] = mapped_column(
        CHAR(32),
        primary_key=True,
        default=generate_uuid,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
    )
