"""Telemetry intake + read endpoints.

POST /api/v1/telemetry/ is unauthenticated for now (TODO Day 5: API key).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryResponse
from app.services import audit_service, monitoring_service
from app.services.monitoring_service import StatusCache
from app.services.permissions import READ_ANY
from app.utils.errors import bad_request

logger = logging.getLogger("telemetry")
router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


class TelemetryIn(BaseModel):
    boiler_id: int
    timestamp: Optional[datetime] = None
    temperature_heat: Optional[Decimal] = None
    pressure: Optional[Decimal] = None
    co_level: Optional[Decimal] = None
    gas_flow: Optional[Decimal] = None
    water_level: Optional[Decimal] = None
    temperature_return: Optional[Decimal] = None
    furnace_draft: Optional[Decimal] = None


class TelemetryAccepted(BaseModel):
    id: int
    boiler_id: int
    timestamp: datetime
    status: str  # normal | warning | critical
    breaches: list = Field(default_factory=list)
    auto_request_id: Optional[int] = None


def _to_param_dict(p: TelemetryIn) -> dict:
    return {
        "temperature_heat": p.temperature_heat,
        "pressure": p.pressure,
        "co_level": p.co_level,
        "gas_flow": p.gas_flow,
        "water_level": p.water_level,
        "temperature_return": p.temperature_return,
        "furnace_draft": p.furnace_draft,
    }


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _ingest_one(session: AsyncSession, payload: TelemetryIn) -> TelemetryAccepted:
    if payload.boiler_id <= 0:
        raise bad_request("boiler_id must be positive")
    timestamp = payload.timestamp or _naive_utc_now()
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

    parameters = _to_param_dict(payload)

    # Evaluate first (so we know status before insert)
    eval_result = await monitoring_service.evaluate(
        session, boiler_id=payload.boiler_id, parameters=parameters,
        auto_create_request=False,  # do it after telemetry is committed
    )

    record = Telemetry(
        boiler_id=payload.boiler_id,
        timestamp=timestamp,
        temperature_heat=payload.temperature_heat,
        pressure=payload.pressure,
        co_level=payload.co_level,
        gas_flow=payload.gas_flow,
        water_level=payload.water_level,
        temperature_return=payload.temperature_return,
        furnace_draft=payload.furnace_draft,
        status=eval_result.overall,
    )
    session.add(record)
    try:
        await session.commit()
    except IntegrityError:
        # Duplicate (boiler_id, timestamp) — idempotent ingest.
        await session.rollback()
        existing = (await session.execute(
            select(Telemetry).where(
                Telemetry.boiler_id == payload.boiler_id,
                Telemetry.timestamp == timestamp,
            )
        )).scalar_one()
        return TelemetryAccepted(
            id=existing.id, boiler_id=existing.boiler_id, timestamp=existing.timestamp,
            status=existing.status, breaches=[], auto_request_id=None,
        )
    await session.refresh(record)

    # Auto-request escalation (separate transaction)
    auto_request_id: Optional[int] = None
    if eval_result.overall == "critical":
        critical_breach = next((b for b in eval_result.breaches if b.kind == "critical"), None)
        if critical_breach is not None:
            try:
                from app.services import request_service

                created = await request_service.create_auto_request(
                    session,
                    boiler_id=payload.boiler_id,
                    parameter_name=critical_breach.parameter,
                    value=str(critical_breach.value),
                    threshold_kind=critical_breach.bound,
                )
                if created is not None:
                    auto_request_id = created.id
                    await audit_service.log(
                        session, user_id=None, action="threshold_breached",
                        entity_type="boiler", entity_id=payload.boiler_id,
                        details={
                            "parameter": critical_breach.parameter,
                            "value": str(critical_breach.value),
                            "kind": critical_breach.bound,
                            "auto_request_id": created.id,
                        },
                        autocommit=True,
                    )
            except Exception:  # noqa: BLE001
                logger.exception("auto-request creation failed for boiler_id=%s", payload.boiler_id)

    accepted = TelemetryAccepted(
        id=record.id,
        boiler_id=record.boiler_id,
        timestamp=record.timestamp,
        status=record.status,
        breaches=[
            {"parameter": b.parameter, "kind": b.kind, "value": str(b.value),
             "bound": b.bound, "threshold_value": str(b.threshold_value)}
            for b in eval_result.breaches
        ],
        auto_request_id=auto_request_id,
    )

    # Broadcast to WebSocket clients (fire-and-forget — telemetry must not fail on WS errors)
    try:
        from app.websocket.monitoring_ws import broadcast_telemetry_update
        dashboard_status = {"normal": "green", "warning": "yellow", "critical": "red"}.get(record.status, "unknown")
        cache_snap = StatusCache.get(payload.boiler_id)
        await broadcast_telemetry_update(
            boiler_id=record.boiler_id,
            timestamp=record.timestamp,
            status=dashboard_status,
            parameters=cache_snap.get("parameters", {}) if cache_snap else {},
            breaches=accepted.breaches,
            auto_request_id=auto_request_id,
        )
    except Exception:
        logger.exception("WS broadcast failed for boiler_id=%s", payload.boiler_id)

    return accepted


@router.post("/", response_model=TelemetryAccepted, status_code=status.HTTP_201_CREATED)
async def post_telemetry(
    payload: TelemetryIn,
    session: AsyncSession = Depends(get_db),
):
    return await _ingest_one(session, payload)


@router.post("/batch", response_model=List[TelemetryAccepted], status_code=status.HTTP_201_CREATED)
async def post_telemetry_batch(
    items: List[TelemetryIn],
    session: AsyncSession = Depends(get_db),
):
    if len(items) > 1000:
        raise bad_request("batch too large (max 1000)")
    out = []
    for it in items:
        out.append(await _ingest_one(session, it))
    return out


@router.get("/{boiler_id}/latest", response_model=Optional[TelemetryResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_latest(boiler_id: int, session: AsyncSession = Depends(get_db)):
    stmt = (
        select(Telemetry)
        .where(Telemetry.boiler_id == boiler_id)
        .order_by(Telemetry.timestamp.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


@router.get("/{boiler_id}/history", response_model=List[TelemetryResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_history(
    boiler_id: int,
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(500, ge=1, le=10000),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Telemetry).where(Telemetry.boiler_id == boiler_id)
    if date_from is not None:
        stmt = stmt.where(Telemetry.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(Telemetry.timestamp <= date_to)
    stmt = stmt.order_by(Telemetry.timestamp.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


@router.get("/all/current", dependencies=[Depends(RoleChecker(READ_ANY))])
async def all_current():
    """Текущие показания всех котельных из in-memory кеша."""
    return [
        {"boiler_id": bid, **snapshot}
        for bid, snapshot in StatusCache.all().items()
    ]
