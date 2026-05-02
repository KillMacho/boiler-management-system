"""Monitoring: dashboard status, active alarms, threshold CRUD."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.boilers import Boiler
from app.models.requests import Request
from app.models.telemetry import Telemetry, Threshold
from app.schemas.telemetry import ThresholdCreate, ThresholdResponse, ThresholdUpdate
from app.services import audit_service
from app.services.monitoring_service import StatusCache
from app.services.permissions import READ_ANY, THRESHOLD_WRITE
from app.services.reference_cache import reference_cache
from app.utils.errors import not_found

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


class BoilerStatus(BaseModel):
    boiler_id: int
    name: str
    status: str  # green | yellow | red | unknown
    parameters: Dict[str, Any] = {}
    breaches: list = []
    last_update: Optional[datetime] = None


@router.get("/status", response_model=List[BoilerStatus], dependencies=[Depends(RoleChecker(READ_ANY))])
async def dashboard_status(session: AsyncSession = Depends(get_db)):
    boilers = list((await session.execute(select(Boiler).order_by(Boiler.id))).scalars().all())
    cache = StatusCache.all()
    out: List[BoilerStatus] = []
    for b in boilers:
        snap = cache.get(b.id)
        if snap:
            out.append(
                BoilerStatus(
                    boiler_id=b.id,
                    name=b.name,
                    status=snap["status"],
                    parameters=snap.get("parameters", {}),
                    breaches=snap.get("breaches", []),
                    last_update=datetime.fromtimestamp(snap["updated_at"], tz=timezone.utc),
                )
            )
        else:
            # Fallback: latest telemetry from DB (no cache yet)
            latest = (await session.execute(
                select(Telemetry).where(Telemetry.boiler_id == b.id).order_by(Telemetry.timestamp.desc()).limit(1)
            )).scalar_one_or_none()
            if latest is None:
                out.append(BoilerStatus(boiler_id=b.id, name=b.name, status="unknown"))
            else:
                dashboard = {"normal": "green", "warning": "yellow", "critical": "red"}.get(latest.status, "unknown")
                out.append(BoilerStatus(
                    boiler_id=b.id, name=b.name, status=dashboard,
                    last_update=latest.timestamp,
                ))
    return out


@router.get("/alarms/active", dependencies=[Depends(RoleChecker(READ_ANY))])
async def active_alarms(session: AsyncSession = Depends(get_db)):
    """Активные аварии = открытые заявки типа 'Авария'."""
    avaria_id = reference_cache.request_type_id("Авария")
    if avaria_id is None:
        return []
    stmt = (
        select(Request)
        .where(
            Request.type_id == avaria_id,
            Request.status.in_(["new", "assigned", "in_progress"]),
        )
        .order_by(Request.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "request_id": r.id,
            "number": r.number,
            "boiler_id": r.boiler_id,
            "status": r.status,
            "source": r.source,
            "description": r.description,
            "created_at": r.created_at,
        }
        for r in rows
    ]


# ---------- thresholds CRUD -----------------------------------------------
@router.get("/thresholds", response_model=List[ThresholdResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_thresholds(
    boiler_id: Optional[int] = Query(None),
    parameter_name: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Threshold)
    if boiler_id is not None:
        stmt = stmt.where(Threshold.boiler_id == boiler_id)
    if parameter_name:
        stmt = stmt.where(Threshold.parameter_name == parameter_name)
    return list((await session.execute(stmt.order_by(Threshold.id))).scalars().all())


@router.post("/thresholds", response_model=ThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_threshold(
    payload: ThresholdCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(THRESHOLD_WRITE)),
):
    obj = Threshold(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_created",
        entity_type="threshold", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.put("/thresholds/{threshold_id}", response_model=ThresholdResponse)
async def update_threshold(
    threshold_id: int,
    payload: ThresholdUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(THRESHOLD_WRITE)),
):
    obj = await session.get(Threshold, threshold_id)
    if obj is None:
        raise not_found("threshold", threshold_id)
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_updated",
        entity_type="threshold", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.delete("/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threshold(
    threshold_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(THRESHOLD_WRITE)),
):
    obj = await session.get(Threshold, threshold_id)
    if obj is None:
        raise not_found("threshold", threshold_id)
    await session.delete(obj)
    await session.commit()
    await audit_service.log(
        session, user_id=user.id, action="entity_hard_deleted",
        entity_type="threshold", entity_id=threshold_id, autocommit=True,
    )
