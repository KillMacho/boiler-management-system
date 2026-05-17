"""Brigade assignment: qualification coverage + 30-day load ranking.

Algorithm:
  1. Fetch required qualifications for request.type_id from work_type_qualifications.
  2. Find brigades that are not inactive AND have no active work_orders
     (status in 'assigned'/'in_progress').
  3. Filter brigades whose members collectively cover ALL required qualifications.
  4. Among qualifying brigades, return the one with the fewest work_orders in last 30 days.
  5. Return None if no suitable brigade exists.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personnel import Brigade, BrigadeMember, EmployeeQualification, WorkTypeQualification
from app.models.requests import Request, WorkOrder

logger = logging.getLogger("brigade_assigner")


class BrigadeAssigner(ABC):
    @abstractmethod
    async def assign(self, session: AsyncSession, request: Request) -> Optional[Brigade]:
        """Pick a brigade for the given request, or None if none suitable."""


class SmartBrigadeAssigner(BrigadeAssigner):
    async def assign(self, session: AsyncSession, request: Request) -> Optional[Brigade]:
        # Шаг 1: определяем, какие квалификации требуются для данного типа заявки
        req_rows = await session.execute(
            select(WorkTypeQualification.qualification_id).where(
                WorkTypeQualification.request_type_id == request.type_id
            )
        )
        required_qual_ids: set[int] = {r[0] for r in req_rows.fetchall()}

        # Шаг 2: берём все активные бригады (не inactive)
        brig_rows = await session.execute(
            select(Brigade).where(Brigade.status != "inactive")
        )
        all_brigades: list[Brigade] = list(brig_rows.scalars().all())
        if not all_brigades:
            logger.warning("no brigades in system for request_id=%s", request.id)
            return None

        # Шаг 3: исключаем занятые бригады (есть активный наряд)
        free_brigades: list[Brigade] = []
        for brigade in all_brigades:
            active_count = (
                await session.execute(
                    select(func.count(WorkOrder.id)).where(
                        WorkOrder.brigade_id == brigade.id,
                        WorkOrder.status.in_(["assigned", "in_progress"]),
                    )
                )
            ).scalar_one()
            if active_count == 0:
                free_brigades.append(brigade)

        if not free_brigades:
            logger.warning("all brigades busy for request_id=%s", request.id)
            return None

        # Шаг 4: бригада проходит только если её члены покрывают все нужные квалификации
        if required_qual_ids:
            qualified: list[Brigade] = []
            for brigade in free_brigades:
                member_qual_rows = await session.execute(
                    select(EmployeeQualification.qualification_id)
                    .join(
                        BrigadeMember,
                        BrigadeMember.employee_id == EmployeeQualification.employee_id,
                    )
                    .where(BrigadeMember.brigade_id == brigade.id)
                )
                member_quals: set[int] = {r[0] for r in member_qual_rows.fetchall()}
                if required_qual_ids.issubset(member_quals):
                    qualified.append(brigade)
        else:
            qualified = free_brigades

        if not qualified:
            logger.warning(
                "no qualified brigades for request_id=%s (required=%s)",
                request.id,
                required_qual_ids,
            )
            return None

        # Шаг 5: выбираем наименее загруженную бригаду за последние 30 дней
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        loads: dict[int, int] = {}
        for brigade in qualified:
            count = (
                await session.execute(
                    select(func.count(WorkOrder.id)).where(
                        WorkOrder.brigade_id == brigade.id,
                        WorkOrder.assigned_at >= cutoff,
                    )
                )
            ).scalar_one()
            loads[brigade.id] = count

        best = min(qualified, key=lambda b: loads[b.id])
        logger.info(
            "assigned brigade_id=%s (30d_load=%s) to request_id=%s",
            best.id,
            loads[best.id],
            request.id,
        )
        return best


# Module-level singleton used by request_service.
brigade_assigner: BrigadeAssigner = SmartBrigadeAssigner()
