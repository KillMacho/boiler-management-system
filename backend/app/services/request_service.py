"""Request lifecycle: classification, priority, creation with auto-assignment,
status transitions with side effects (act generation, material write-off, close).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requests import Act, Request, WorkOrder
from app.schemas.requests import RequestCreate
from app.services import audit_service, notification_service, number_generator
from app.services.brigade_assigner import brigade_assigner
from app.services.reference_cache import reference_cache
from app.utils.errors import bad_request, conflict, not_found

logger = logging.getLogger("request_service")

# ── classification ────────────────────────────────────────────────────────────
_AVARIA_PATTERNS = re.compile(
    r"авари|не\s+работает|не\s+греет|тече|возгор|задымл|пожар|взрыв",
    re.IGNORECASE,
)
_PLAN_PATTERNS = re.compile(
    r"плановы|регламент|то\s+по\s+плану|периодич",
    re.IGNORECASE,
)


def classify_by_description(text: Optional[str]) -> str:
    """Return one of: 'Авария', 'Плановое ТО', 'Текущий ремонт'."""
    if not text:
        return "Текущий ремонт"
    if _AVARIA_PATTERNS.search(text):
        return "Авария"
    if _PLAN_PATTERNS.search(text):
        return "Плановое ТО"
    return "Текущий ремонт"


# ── priority mapping ──────────────────────────────────────────────────────────
_PRIORITY_BY_TYPE = {
    "Авария": "Критический",
    "Аварийное ТО": "Высокий",
    "Плановое ТО": "Средний",
    "Текущий ремонт": "Средний",
    "Предиктивное ТО": "Средний",
}


def compute_priority_name(type_name: str) -> str:
    return _PRIORITY_BY_TYPE.get(type_name, "Средний")


# ── state machine ─────────────────────────────────────────────────────────────
VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"assigned", "cancelled", "needs_manual_assignment"},
    "needs_manual_assignment": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled", "waiting_materials"},
    "waiting_materials": {"assigned", "cancelled"},
    "in_progress": {"work_completed", "completed", "cancelled"},  # 'completed' kept for compat
    "work_completed": {"act_generated"},
    "act_generated": {"closed"},
    "completed": {"closed"},  # Day 3 backward-compat path
    "closed": set(),
    "cancelled": set(),
}


# ── create ────────────────────────────────────────────────────────────────────
async def create_request(
    session: AsyncSession,
    payload: RequestCreate,
    *,
    user_id: Optional[int],
    source: Optional[str] = None,
) -> Tuple[Request, Optional[WorkOrder], Optional[str]]:
    """Create a request with auto-classification, smart priority, and brigade.

    Returns (request, work_order_or_None, warning_or_None).
    """
    actual_source = source or payload.source

    # 1. Classify type if missing
    type_id = payload.type_id
    if not type_id:
        type_name = classify_by_description(payload.description)
        type_id = reference_cache.request_type_id(type_name)
        if type_id is None:
            raise bad_request(f"Unknown request type after classification: {type_name}")
    else:
        type_name = reference_cache.request_type_name(type_id) or ""

    # 2. Smart priority: source-aware + boiler-name boost
    priority_id = payload.priority_id
    if not priority_id:
        from app.services.priority_calculator import compute_priority_name as smart_priority

        priority_name = await smart_priority(
            session,
            type_name=type_name,
            source=actual_source or "web",
            boiler_id=payload.boiler_id,
            reference_cache=reference_cache,
        )
        priority_id = reference_cache.request_priority_id(priority_name)
    if not priority_id:
        raise bad_request("Unable to resolve priority")

    # 3. Number
    number = payload.number or await number_generator.next_request_number(session)

    request = Request(
        number=number,
        boiler_id=payload.boiler_id,
        type_id=type_id,
        priority_id=priority_id,
        description=payload.description,
        source=actual_source or "web",
        status="new",
        created_by=user_id,
    )
    session.add(request)
    await session.flush()

    await audit_service.log(
        session,
        user_id=user_id,
        action="request_created",
        entity_type="request",
        entity_id=request.id,
        details={
            "number": request.number,
            "boiler_id": request.boiler_id,
            "type_id": request.type_id,
            "priority_id": request.priority_id,
            "source": request.source,
        },
    )

    # 4. Brigade assignment
    work_order: Optional[WorkOrder] = None
    warning: Optional[str] = None
    brigade = await brigade_assigner.assign(session, request)
    if brigade is None:
        warning = "no_brigade_available"
        await audit_service.log(
            session,
            user_id=user_id,
            action="brigade_assignment_failed",
            entity_type="request",
            entity_id=request.id,
        )
    else:
        work_order = WorkOrder(
            request_id=request.id,
            brigade_id=brigade.id,
            status="assigned",
        )
        session.add(work_order)
        request.status = "assigned"
        await session.flush()
        await audit_service.log(
            session,
            user_id=user_id,
            action="work_order_created",
            entity_type="work_order",
            entity_id=work_order.id,
            details={"request_id": request.id, "brigade_id": brigade.id},
        )

    await session.commit()
    await session.refresh(request)

    await notification_service.send(
        {"event": "request.created", "request_id": request.id, "number": request.number}
    )
    return request, work_order, warning


# ── auto-assign (post-creation) ───────────────────────────────────────────────
async def auto_assign_brigade(
    session: AsyncSession,
    *,
    request_id: int,
    user_id: Optional[int],
) -> Tuple[Request, Optional[WorkOrder], Optional[str]]:
    """Re-run brigade assignment on an existing unassigned request."""
    request = await session.get(Request, request_id)
    if request is None:
        raise not_found("request", request_id)

    if request.status not in ("new", "needs_manual_assignment"):
        raise conflict(
            f"Auto-assign only possible from 'new'/'needs_manual_assignment', "
            f"current status={request.status!r}"
        )

    brigade = await brigade_assigner.assign(session, request)
    if brigade is None:
        request.status = "needs_manual_assignment"
        await session.commit()
        await session.refresh(request)
        return request, None, "no_brigade_available"

    work_order = WorkOrder(
        request_id=request.id,
        brigade_id=brigade.id,
        status="assigned",
    )
    session.add(work_order)
    request.status = "assigned"
    await session.flush()
    await audit_service.log(
        session,
        user_id=user_id,
        action="brigade_auto_assigned",
        entity_type="request",
        entity_id=request.id,
        details={"brigade_id": brigade.id},
    )
    await session.commit()
    await session.refresh(request)
    return request, work_order, None


async def manual_assign_brigade(
    session: AsyncSession,
    *,
    request_id: int,
    brigade_id: int,
    user_id: Optional[int],
) -> Tuple[Request, WorkOrder]:
    """Manually assign a specific brigade to a request."""
    from app.models.personnel import Brigade

    request = await session.get(Request, request_id)
    if request is None:
        raise not_found("request", request_id)

    if request.status not in ("new", "needs_manual_assignment"):
        raise conflict(
            f"Manual assign only from 'new'/'needs_manual_assignment', status={request.status!r}"
        )

    brigade = await session.get(Brigade, brigade_id)
    if brigade is None:
        raise not_found("brigade", brigade_id)

    work_order = WorkOrder(
        request_id=request.id,
        brigade_id=brigade.id,
        status="assigned",
    )
    session.add(work_order)
    request.status = "assigned"
    await session.flush()
    await audit_service.log(
        session,
        user_id=user_id,
        action="brigade_manual_assigned",
        entity_type="request",
        entity_id=request.id,
        details={"brigade_id": brigade_id},
    )
    await session.commit()
    await session.refresh(request)
    return request, work_order


# ── auto-request from monitoring ──────────────────────────────────────────────
async def find_open_avaria_for_boiler(
    session: AsyncSession, boiler_id: int
) -> Optional[Request]:
    avaria_type_id = reference_cache.request_type_id("Авария")
    if avaria_type_id is None:
        return None
    stmt = (
        select(Request)
        .where(
            Request.boiler_id == boiler_id,
            Request.type_id == avaria_type_id,
            Request.status.in_(["new", "assigned", "in_progress"]),
        )
        .order_by(Request.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_auto_request(
    session: AsyncSession,
    *,
    boiler_id: int,
    parameter_name: str,
    value,
    threshold_kind: str,
) -> Optional[Request]:
    """Create an emergency request from monitoring. Deduplicates by open Авария."""
    existing = await find_open_avaria_for_boiler(session, boiler_id)
    if existing is not None:
        logger.debug(
            "skipping auto-request: open Авария id=%s already exists for boiler_id=%s",
            existing.id,
            boiler_id,
        )
        return None

    avaria_type_id = reference_cache.request_type_id("Авария")
    krit_priority_id = reference_cache.request_priority_id("Критический")
    if avaria_type_id is None or krit_priority_id is None:
        logger.error("reference cache missing Авария/Критический — cannot auto-create")
        return None

    payload = RequestCreate(
        number="",
        boiler_id=boiler_id,
        type_id=avaria_type_id,
        priority_id=krit_priority_id,
        description=(
            f"Параметр {parameter_name}={value} вышел за {threshold_kind}-порог. "
            f"Авто-заявка от системы мониторинга."
        ),
        source="monitoring",
        status="new",
    )

    try:
        request, _wo, _warn = await create_request(
            session, payload, user_id=None, source="monitoring"
        )
    except IntegrityError as exc:
        await session.rollback()
        logger.info("auto-request dedup via IntegrityError: %s", exc.orig)
        return None

    await audit_service.log(
        session,
        user_id=None,
        action="auto_request_created",
        entity_type="request",
        entity_id=request.id,
        details={
            "boiler_id": boiler_id,
            "parameter_name": parameter_name,
            "value": value,
            "threshold_kind": threshold_kind,
        },
        autocommit=True,
    )
    return request


# ── status transition with side effects ───────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_latest_work_order(session: AsyncSession, request_id: int) -> Optional[WorkOrder]:
    stmt = (
        select(WorkOrder)
        .where(WorkOrder.request_id == request_id)
        .order_by(WorkOrder.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _handle_act_generated(
    session: AsyncSession, request: Request, user_id: Optional[int]
) -> None:
    """Create Act record when request transitions to 'act_generated'."""
    wo = await _get_latest_work_order(session, request.id)
    if wo is None:
        logger.warning("act_generated: no work_order for request_id=%s", request.id)
        return

    existing = (
        await session.execute(select(Act).where(Act.work_order_id == wo.id))
    ).scalar_one_or_none()
    if existing is not None:
        return  # Act already exists

    # Calculate total_amount from outcome movements for this work order
    from app.models.warehouse import MaterialMovement, Material
    from sqlalchemy import func as sqlfunc

    amount_result = await session.execute(
        select(sqlfunc.sum(MaterialMovement.quantity * Material.price))
        .join(Material, Material.id == MaterialMovement.material_id)
        .where(
            MaterialMovement.work_order_id == wo.id,
            MaterialMovement.movement_type == "outcome",
        )
    )
    total_amount = amount_result.scalar_one_or_none() or Decimal("0")

    act = Act(
        work_order_id=wo.id,
        number=await number_generator.next_act_number(session),
        total_amount=total_amount,
        pdf_path="/placeholder.pdf",
    )
    session.add(act)
    await session.flush()
    await audit_service.log(
        session,
        user_id=user_id,
        action="act_generated",
        entity_type="act",
        entity_id=act.id,
        details={"request_id": request.id, "total_amount": str(total_amount)},
    )
    logger.info(
        "act id=%s created for request_id=%s amount=%s", act.id, request.id, total_amount
    )


async def _handle_closed(
    session: AsyncSession, request: Request, user_id: Optional[int]
) -> None:
    """Side effects when request is closed: complete open work order, audit."""
    wo = await _get_latest_work_order(session, request.id)
    if wo and wo.status not in ("completed", "closed", "cancelled"):
        wo.status = "completed"
        wo.completed_at = _now()

    await audit_service.log(
        session,
        user_id=user_id,
        action="request_closed",
        entity_type="request",
        entity_id=request.id,
        details={"boiler_id": request.boiler_id},
    )


async def change_status(
    session: AsyncSession,
    *,
    request_id: int,
    new_status: str,
    user_id: Optional[int],
) -> Request:
    request = await session.get(Request, request_id)
    if request is None:
        raise not_found("request", request_id)

    allowed = VALID_TRANSITIONS.get(request.status, set())
    if new_status not in allowed:
        raise conflict(
            f"Invalid transition {request.status!r} -> {new_status!r}"
        )

    old = request.status
    request.status = new_status

    if new_status in {"closed", "cancelled"} and request.closed_at is None:
        request.closed_at = _now()

    # Side effects
    if new_status == "act_generated":
        await _handle_act_generated(session, request, user_id)
    elif new_status == "closed":
        await _handle_closed(session, request, user_id)

    await audit_service.log(
        session,
        user_id=user_id,
        action="request_status_changed",
        entity_type="request",
        entity_id=request.id,
        details={"from": old, "to": new_status},
    )
    await session.commit()
    await session.refresh(request)
    return request
