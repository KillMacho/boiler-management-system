"""Work order lifecycle: start, complete (with material write-off), photos, checklist."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requests import (
    Act,
    Request,
    WorkOrder,
    WorkOrderChecklistItem,
    WorkOrderPhoto,
)
from app.services import audit_service, number_generator
from app.utils.errors import conflict, not_found


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def start(
    session: AsyncSession, *, work_order_id: int, user_id: Optional[int]
) -> WorkOrder:
    wo = await session.get(WorkOrder, work_order_id)
    if wo is None:
        raise not_found("work_order", work_order_id)
    if wo.status not in ("assigned", "waiting_materials"):
        raise conflict(f"Work order in status {wo.status!r} cannot be started")
    wo.status = "in_progress"
    wo.started_at = _now()
    await audit_service.log(
        session,
        user_id=user_id,
        action="work_order_started",
        entity_type="work_order",
        entity_id=wo.id,
    )
    await session.commit()
    await session.refresh(wo)
    return wo


async def complete(
    session: AsyncSession,
    *,
    work_order_id: int,
    user_id: Optional[int],
    notes: Optional[str] = None,
    total_amount: Decimal = Decimal("0"),
    create_act: bool = False,  # Act is now created via request status → act_generated
) -> WorkOrder:
    """Complete a work order.

    Day 4 changes vs Day 3:
    - Writes off all reserved materials automatically.
    - Sets the parent request to 'work_completed' (not 'completed').
    - Does NOT auto-create Act (deferred to request status → 'act_generated').
    - create_act=True is kept for backward compat if caller explicitly requests it.
    """
    wo = await session.get(WorkOrder, work_order_id)
    if wo is None:
        raise not_found("work_order", work_order_id)
    if wo.status != "in_progress":
        raise conflict(f"Work order in status {wo.status!r} cannot be completed")

    wo.status = "completed"
    wo.completed_at = _now()

    # Автоматически списываем все зарезервированные материалы при завершении наряда
    from app.services.warehouse_service import write_off_for_work_order

    lines_written = await write_off_for_work_order(
        session, work_order_id=work_order_id, user_id=user_id
    )

    # Переводим родительскую заявку в work_completed, если она ещё in_progress
    request = await session.get(Request, wo.request_id)
    if request and request.status == "in_progress":
        from app.services.request_service import VALID_TRANSITIONS

        if "work_completed" in VALID_TRANSITIONS.get(request.status, set()):
            request.status = "work_completed"

    if create_act:
        existing_act = (
            await session.execute(select(Act).where(Act.work_order_id == wo.id))
        ).scalar_one_or_none()
        if existing_act is None:
            act = Act(
                work_order_id=wo.id,
                number=await number_generator.next_act_number(session),
                total_amount=total_amount,
                pdf_path="/placeholder.pdf",
            )
            session.add(act)

    await audit_service.log(
        session,
        user_id=user_id,
        action="work_order_completed",
        entity_type="work_order",
        entity_id=wo.id,
        details={
            "notes": notes,
            "total_amount": str(total_amount),
            "lines_written_off": lines_written,
        },
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(wo)
    return wo


async def toggle_checklist_item(
    session: AsyncSession,
    *,
    work_order_id: int,
    item_id: int,
    is_completed: bool,
    user_id: Optional[int],
) -> WorkOrderChecklistItem:
    item = await session.get(WorkOrderChecklistItem, item_id)
    if item is None or item.work_order_id != work_order_id:
        raise not_found("checklist_item", item_id)
    item.is_completed = is_completed
    item.completed_at = _now() if is_completed else None
    await audit_service.log(
        session,
        user_id=user_id,
        action="checklist_item_toggled",
        entity_type="work_order_checklist_item",
        entity_id=item.id,
        details={"is_completed": is_completed},
    )
    await session.commit()
    await session.refresh(item)
    return item


async def add_photo(
    session: AsyncSession,
    *,
    work_order_id: int,
    file_path: str,
    user_id: Optional[int],
) -> WorkOrderPhoto:
    photo = WorkOrderPhoto(work_order_id=work_order_id, file_path=file_path)
    session.add(photo)
    await audit_service.log(
        session,
        user_id=user_id,
        action="work_order_photo_added",
        entity_type="work_order",
        entity_id=work_order_id,
        details={"file_path": file_path},
    )
    await session.commit()
    await session.refresh(photo)
    return photo


# Возвращает наряды для мобильного приложения бригадира — только его бригады
async def list_my_brigade_work_orders(
    session: AsyncSession, *, brigade_ids: List[int], skip: int, limit: int
) -> List[WorkOrder]:
    if not brigade_ids:
        return []
    stmt = (
        select(WorkOrder)
        .where(WorkOrder.brigade_id.in_(brigade_ids))
        .order_by(WorkOrder.assigned_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
