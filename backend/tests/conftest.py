"""Pytest fixtures: AsyncClient against the FastAPI app, against the real DB.

We override the production engine with a NullPool-backed one so connections
do not survive across tests (each pytest-asyncio test runs in its own loop,
and pooled aioodbc connections cannot be closed from a different loop).
"""
from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import pytest_asyncio

from app.config import settings
from app.database import get_db
from app.main import app
from app.services.reference_cache import reference_cache

# NullPool — соединения не переживают между тестами; каждый тест получает чистое соединение
_test_engine = create_async_engine(
    settings.sqlalchemy_async_url,
    poolclass=NullPool,
)
_TestSession = async_sessionmaker(
    bind=_test_engine,
    expire_on_commit=False,
)


async def _get_test_db() -> AsyncGenerator:
    async with _TestSession() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Подменяем зависимость get_db на тестовую сессию для всего тестового сеанса
app.dependency_overrides[get_db] = _get_test_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _warmup_reference_cache() -> None:
    """Warm reference_cache before any test runs (startup event doesn't fire in ASGI transport)."""
    # startup-событие FastAPI не срабатывает в ASGI-транспорте — греем кеш вручную
    async with _TestSession() as session:
        await reference_cache.warmup(session)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    # Каждый тест получает свежий AsyncClient с ASGI-транспортом (без реального сервера)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
