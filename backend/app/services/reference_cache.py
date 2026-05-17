"""Read-heavy lookup tables cached in memory after startup."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requests import RequestPriority, RequestType

logger = logging.getLogger("reference_cache")


# Кеш типов и приоритетов заявок: загружается один раз при старте, не меняется в рантайме
class ReferenceCache:
    request_types: Dict[str, int] = {}
    request_types_by_id: Dict[int, str] = {}
    request_priorities: Dict[str, int] = {}
    request_priorities_by_id: Dict[int, str] = {}
    _ready: bool = False

    @classmethod
    def is_ready(cls) -> bool:
        return cls._ready

    @classmethod
    async def warmup(cls, session: AsyncSession) -> None:
        # Заполняем двусторонние словари name<->id для быстрого поиска без БД
        rt = (await session.execute(select(RequestType))).scalars().all()
        cls.request_types = {row.name: row.id for row in rt}
        cls.request_types_by_id = {row.id: row.name for row in rt}

        rp = (await session.execute(select(RequestPriority))).scalars().all()
        cls.request_priorities = {row.name: row.id for row in rp}
        cls.request_priorities_by_id = {row.id: row.name for row in rp}
        cls._ready = True
        logger.info(
            "reference cache warmed: request_types=%d, priorities=%d",
            len(rt),
            len(rp),
        )

    @classmethod
    def request_type_id(cls, name: str) -> Optional[int]:
        return cls.request_types.get(name)

    @classmethod
    def request_priority_id(cls, name: str) -> Optional[int]:
        return cls.request_priorities.get(name)

    @classmethod
    def request_type_name(cls, type_id: int) -> Optional[str]:
        return cls.request_types_by_id.get(type_id)


reference_cache = ReferenceCache()
