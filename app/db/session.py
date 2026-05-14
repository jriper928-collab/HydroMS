"""Async SQLAlchemy engine and session factory for SQLite.
Applies WAL mode and busy timeout via URL parameters for aiosqlite compatibility."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

PRAGMA_PARAMS = "?pragma=journal_mode(WAL)&pragma=busy_timeout(5000)"

engine = create_async_engine(
    settings.DATABASE_URL + PRAGMA_PARAMS,
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
