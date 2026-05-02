"""Maintenance planning: generate schedule, update next_due_date after completion."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import MaintenancePlanItem, MaintenanceRegulation, MaintenanceSchedule
from app.services import audit_service

logger = logging.getLogger("maintenance_planner")


@dataclass
class GeneratePlanResult:
    schedule_id: int
    items_created: int
    brigades_assigned: int


async def generate_plan(
    session: AsyncSession,
    *,
    period_start: date,
    period_end: date,
    user_id: Optional[int] = None,
) -> GeneratePlanResult:
    """Generate a maintenance plan for the given period.

    Steps:
      1. Create MaintenanceSchedule (status='draft').
      2. Find all regulations with next_due_date in [period_start, period_end].
      3. For each, create a MaintenancePlanItem and attempt brigade assignment.
    """
    from app.services.brigade_assigner import brigade_assigner
    from app.services.reference_cache import reference_cache
    from app.models.requests import Request

    # 1. Create schedule
    schedule = MaintenanceSchedule(
        period_start=period_start,
        period_end=period_end,
        status="draft",
    )
    session.add(schedule)
    await session.flush()
    schedule_id = schedule.id

    # 2. Find regulations due in period (eager-load equipment)
    reg_rows = await session.execute(
        select(MaintenanceRegulation)
        .options(selectinload(MaintenanceRegulation.equipment))
        .options(selectinload(MaintenanceRegulation.maintenance_type))
        .where(
            MaintenanceRegulation.next_due_date >= period_start,
            MaintenanceRegulation.next_due_date <= period_end,
        )
    )
    regulations = list(reg_rows.scalars().all())

    items_created = 0
    brigades_assigned = 0
    planovoe_type_id = reference_cache.request_type_id("Плановое ТО")

    for reg in regulations:
        # 3a. Create plan item
        item = MaintenancePlanItem(
            schedule_id=schedule_id,
            equipment_id=reg.equipment_id,
            maintenance_type_id=reg.maintenance_type_id,
            planned_date=reg.next_due_date,
            status="planned",
        )
        session.add(item)
        await session.flush()
        items_created += 1

        # 3b. Try to assign a brigade using a fake Request for type lookup
        if planovoe_type_id:
            fake_request = Request(
                id=0,
                type_id=planovoe_type_id,
                boiler_id=reg.equipment.boiler_id,
                number="",
                priority_id=1,
                source="maintenance",
                status="new",
            )
            try:
                brigade = await brigade_assigner.assign(session, fake_request)
                if brigade:
                    item.assigned_brigade_id = brigade.id
                    brigades_assigned += 1
            except Exception:
                logger.warning("brigade assignment failed for plan_item id=%s", item.id)

    await audit_service.log(
        session,
        user_id=user_id,
        action="maintenance_plan_generated",
        entity_type="maintenance_schedule",
        entity_id=schedule_id,
        details={
            "period_start": str(period_start),
            "period_end": str(period_end),
            "items_created": items_created,
        },
    )
    await session.commit()
    return GeneratePlanResult(
        schedule_id=schedule_id,
        items_created=items_created,
        brigades_assigned=brigades_assigned,
    )


async def approve_plan_item(
    session: AsyncSession,
    *,
    item_id: int,
    user_id: Optional[int] = None,
) -> MaintenancePlanItem:
    """Approve a plan item: change status → 'approved' and create a Плановое ТО request."""
    from app.services import request_service
    from app.services.reference_cache import reference_cache
    from app.schemas.requests import RequestCreate

    item = await session.get(MaintenancePlanItem, item_id)
    if item is None:
        from app.utils.errors import not_found
        raise not_found("maintenance_plan_item", item_id)

    if item.status == "approved":
        return item

    # Load equipment for boiler_id
    from app.models.maintenance import MaintenancePlanItem as MPI
    item_with_eq = (
        await session.execute(
            select(MPI)
            .options(selectinload(MPI.equipment))
            .where(MPI.id == item_id)
        )
    ).scalar_one()

    boiler_id = item_with_eq.equipment.boiler_id
    planovoe_type_id = reference_cache.request_type_id("Плановое ТО")
    sredny_priority_id = reference_cache.request_priority_id("Средний")

    payload = RequestCreate(
        boiler_id=boiler_id,
        description=(
            f"Плановое ТО: оборудование #{item.equipment_id}, "
            f"плановая дата {item.planned_date}. "
            f"Сгенерировано из плана #{item.schedule_id}."
        ),
        source="maintenance",
        type_id=planovoe_type_id,
        priority_id=sredny_priority_id,
    )

    request, wo, _ = await request_service.create_request(
        session, payload, user_id=user_id, source="maintenance"
    )

    # After create_request commits, refresh item
    item = await session.get(MaintenancePlanItem, item_id)
    item.status = "approved"
    if wo and not item.assigned_brigade_id:
        item.assigned_brigade_id = wo.brigade_id

    await audit_service.log(
        session,
        user_id=user_id,
        action="plan_item_approved",
        entity_type="maintenance_plan_item",
        entity_id=item_id,
        details={"request_id": request.id},
    )
    await session.commit()
    await session.refresh(item)
    return item


async def get_upcoming_regulations(
    session: AsyncSession, *, days_ahead: int = 7
) -> list[MaintenanceRegulation]:
    """Return regulations with next_due_date within the next N days."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    rows = await session.execute(
        select(MaintenanceRegulation)
        .options(
            selectinload(MaintenanceRegulation.equipment),
            selectinload(MaintenanceRegulation.maintenance_type),
        )
        .where(
            MaintenanceRegulation.next_due_date >= today,
            MaintenanceRegulation.next_due_date <= cutoff,
        )
        .order_by(MaintenanceRegulation.next_due_date)
    )
    return list(rows.scalars().all())


async def update_regulation_after_completion(
    session: AsyncSession,
    *,
    regulation_id: int,
    completed_at,
) -> MaintenanceRegulation:
    """Recalculate next_due_date after a maintenance task is performed."""
    from datetime import datetime

    reg = await session.get(MaintenanceRegulation, regulation_id)
    if reg is None:
        return None

    if isinstance(completed_at, datetime):
        completed_at = completed_at.date()

    reg.last_performed_at = completed_at
    reg.next_due_date = completed_at + timedelta(days=reg.maintenance_type.periodicity_days)
    await session.flush()
    return reg
