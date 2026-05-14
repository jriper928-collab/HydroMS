"""Database initialisation helper — creates all tables on startup."""

from app.db.session import engine
from app.models.base import Base
from app.models.user import User  # noqa: F401 — ensure model is imported
from app.models.video import Video  # noqa: F401
from app.models.location import Location  # noqa: F401


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
