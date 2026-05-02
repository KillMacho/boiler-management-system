"""Request lifecycle: classification, priority, creation with auto-assignment,
status transitions. The hot path of the system.
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.requests import Request, WorkOrder
from app.schemas.requests import RequestCreate
from app.services import audit_service, notification_service, number_generator
from app.services.brigade_assigner import brigade_assigner
from app.services.reference_cache import reference_cache
from app.utils.errors import bad_request, conflict, not_found

logger = logging.getLogger("request_service")

# --- классификация --------------------------------------------------------
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


# --- приоритеты по типу ---------------------------------------------------
_PRIORITY_BY_TYPE = {
    "Авария": "Критический",
    "Аварийное ТО": "Высокий",
    "Плановое ТО": "Средний",
    "Текущий ремонт": "Средний",
    "Предиктивное ТО": "Средний",
}


def compute_priority_name(type_name: str) -> str:
    return _PRIORITY_BY_TYPE.get(type_name, "Средний")


# --- транзитивные переходы статусов ---------------------------------------
VALID_TRANSITIONS = {
    "new": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


# --- основной create -------------------------------------------------------
async def create_request(
    session: AsyncSession,
    payload: RequestCreate,
    *,
    user_id: Optional[int],
    source: Optional[str] = None,
) -> Tuple[Request, Optional[WorkOrder], Optional[str]]:
    """Create a request with auto-classification, priority, and brigade.

    Returns (request, work_order_or_None, warning_or_None).
    Caller commits — this function uses session transactions internally only
    for the work_orders + audit insert.
    """
    actual_source = source or payload.source

    # 1. classify type if missing
    type_id = payload.type_id
    if not type_id:
        type_name = classify_by_description(payload.description)
        type_id = reference_cache.request_type_id(type_name)
        if type_id is None:
            raise bad_request(f"Unknown request type after classification: {type_name}")
    else:
        type_name = reference_cache.request_type_name(type_id) or ""

    # 2. priority
    priority_id = payload.priority_id
    if not priority_id and type_name:
        priority_name = compute_priority_name(type_name)
        priority_id = reference_cache.request_priority_id(priority_name)
    if not priority_id:
        raise bad_request("Unable to resolve priority")

    # 3. number
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
    await session.flush()  # need request.id before audit

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

    # 4. brigade assignment + work order
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
    # eager-refresh relationships used in response serialization
    await session.refresh(request)

    await notification_service.send(
        {"event": "request.created", "request_id": request.id, "number": request.number}
    )
    return request, work_order, warning


# --- авто-заявка от monitoring --------------------------------------------
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
        number="",  # will be replaced below
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
        # Filtered unique index hit — concurrent creator won, ours rolls back.
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


# --- смена статуса --------------------------------------------------------
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
        from datetime import datetime, timezone

        request.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)

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
