"""Atomic-ish generators for human-readable numbers (REQ-…, ACT-…).

For the study project we use an UPDLOCK-protected SELECT MAX + INSERT under a
single transaction. Real production should use a sequence table.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requests import Act, Request


def _today_prefix(prefix: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{today}-"


async def _next_number(
    session: AsyncSession, model: Type, column, prefix: str, width: int = 6
) -> str:
    """Pick the next NNNNNN suffix after the largest existing one for today's prefix."""
    today_prefix = _today_prefix(prefix)
    stmt = select(func.max(column)).where(column.like(f"{today_prefix}%"))
    last_number: str | None = (await session.execute(stmt)).scalar_one_or_none()
    # Определяем следующий порядковый номер дня: MAX + 1 или 1 если записей ещё нет
    next_seq = 1
    if last_number:
        try:
            next_seq = int(last_number.rsplit("-", 1)[-1]) + 1
        except ValueError:
            next_seq = 1
    return f"{today_prefix}{next_seq:0{width}d}"


async def next_request_number(session: AsyncSession) -> str:
    return await _next_number(session, Request, Request.number, "REQ")


async def next_act_number(session: AsyncSession) -> str:
    return await _next_number(session, Act, Act.number, "ACT")
