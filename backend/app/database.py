"""Async SQLAlchemy engine and session factory."""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.sqlalchemy_async_url,
    echo=settings.app_debug and False,  # set True for SQL log
    pool_pre_ping=True,
    pool_size=20,          # bumped from 10 for concurrent telemetry
    max_overflow=30,       # bumped from 20
    pool_timeout=30.0,     # explicit timeout instead of default 30s
    pool_recycle=3600,     # recycle connections every 1h (avoid stale connections)
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
