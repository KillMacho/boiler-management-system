"""BrigadeAssigner interface + stub implementation for Day 3.

TODO Day 4: real ranking by qualifications, current load, location.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personnel import Brigade
from app.models.requests import Request

logger = logging.getLogger("brigade_assigner")


class BrigadeAssigner(ABC):
    @abstractmethod
    async def assign(
        self, session: AsyncSession, request: Request
    ) -> Optional[Brigade]:
        """Pick a brigade for the given request, or None if none available."""


class StubBrigadeAssigner(BrigadeAssigner):
    """Returns the first active brigade. Intentionally naive — Day 4 replaces."""

    async def assign(
        self, session: AsyncSession, request: Request
    ) -> Optional[Brigade]:
        stmt = (
            select(Brigade)
            .where(Brigade.status == "active")
            .order_by(Brigade.id)
            .limit(1)
        )
        brigade = (await session.execute(stmt)).scalar_one_or_none()
        if brigade is None:
            logger.warning("no active brigades available for request_id=%s", request.id)
        return brigade


# Default singleton — wired in services.request_service via constructor injection.
brigade_assigner: BrigadeAssigner = StubBrigadeAssigner()
