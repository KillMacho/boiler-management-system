"""CRUD for maintenance: types, regulations, schedules, plan_items.
Also: generate-plan, upcoming regulations, approve plan item.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.maintenance import (
    MaintenancePlanItem,
    MaintenanceRegulation,
    MaintenanceSchedule,
    MaintenanceType,
)
from app.schemas.maintenance import (
    MaintenancePlanItemCreate,
    MaintenancePlanItemResponse,
    MaintenancePlanItemUpdate,
    MaintenanceRegulationCreate,
    MaintenanceRegulationResponse,
    MaintenanceRegulationUpdate,
    MaintenanceScheduleCreate,
    MaintenanceScheduleResponse,
    MaintenanceScheduleUpdate,
    MaintenanceTypeCreate,
    MaintenanceTypeResponse,
    MaintenanceTypeUpdate,
)
from app.services import audit_service
from app.services.crud_base import CRUDBase
from app.services.permissions import MAINTENANCE_WRITE, READ_ANY
from app.utils.errors import not_found

router = APIRouter(prefix="/api/v1", tags=["maintenance"])

# Все сущности ТО используют жёсткое удаление (soft_delete_status=None)
type_crud = CRUDBase[MaintenanceType, MaintenanceTypeCreate, MaintenanceTypeUpdate](MaintenanceType, soft_delete_status=None)
reg_crud = CRUDBase[MaintenanceRegulation, MaintenanceRegulationCreate, MaintenanceRegulationUpdate](MaintenanceRegulation, soft_delete_status=None)
sched_crud = CRUDBase[MaintenanceSchedule, MaintenanceScheduleCreate, MaintenanceScheduleUpdate](MaintenanceSchedule, soft_delete_status=None)
item_crud = CRUDBase[MaintenancePlanItem, MaintenancePlanItemCreate, MaintenancePlanItemUpdate](MaintenancePlanItem, soft_delete_status=None)


# ---------- types ----------------------------------------------------------
@router.get("/maintenance-types/", response_model=List[MaintenanceTypeResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_maint_types(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await type_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/maintenance-types/", response_model=MaintenanceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_maint_type(
    payload: MaintenanceTypeCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await type_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="maintenance_type", entity_id=obj.id, autocommit=True)
    return obj


# ---------- regulations ----------------------------------------------------
@router.get("/regulations/", response_model=List[MaintenanceRegulationResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_regulations(
    pagination: PaginationParams = Depends(get_pagination),
    equipment_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    extra = [MaintenanceRegulation.equipment_id == equipment_id] if equipment_id else []
    return await reg_crud.list(session, skip=pagination.skip, limit=pagination.limit, extra_filters=extra)


@router.post("/regulations/", response_model=MaintenanceRegulationResponse, status_code=status.HTTP_201_CREATED)
async def create_regulation(
    payload: MaintenanceRegulationCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await reg_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="maintenance_regulation", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/regulations/{reg_id}", response_model=MaintenanceRegulationResponse)
async def update_regulation(
    reg_id: int,
    payload: MaintenanceRegulationUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await reg_crud.get(session, reg_id)
    if obj is None:
        raise not_found("regulation", reg_id)
    obj = await reg_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="maintenance_regulation", entity_id=obj.id, autocommit=True)
    return obj


# ---------- schedules ------------------------------------------------------
@router.get("/schedules/", response_model=List[MaintenanceScheduleResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_schedules(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
):
    extra = [MaintenanceSchedule.status == status_filter] if status_filter else []
    return await sched_crud.list(session, skip=pagination.skip, limit=pagination.limit, extra_filters=extra)


@router.post("/schedules/", response_model=MaintenanceScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: MaintenanceScheduleCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await sched_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="maintenance_schedule", entity_id=obj.id, autocommit=True)
    return obj


# ---------- plan items -----------------------------------------------------
@router.get("/plan-items/", response_model=List[MaintenancePlanItemResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_plan_items(
    pagination: PaginationParams = Depends(get_pagination),
    schedule_id: Optional[int] = Query(None),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(MaintenancePlanItem)
    if schedule_id is not None:
        stmt = stmt.where(MaintenancePlanItem.schedule_id == schedule_id)
    if date_from is not None:
        stmt = stmt.where(MaintenancePlanItem.planned_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MaintenancePlanItem.planned_date <= date_to)
    stmt = stmt.order_by(MaintenancePlanItem.planned_date).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/plan-items/", response_model=MaintenancePlanItemResponse, status_code=status.HTTP_201_CREATED)
async def create_plan_item(
    payload: MaintenancePlanItemCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await item_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="maintenance_plan_item", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/plan-items/{item_id}", response_model=MaintenancePlanItemResponse)
async def update_plan_item(
    item_id: int,
    payload: MaintenancePlanItemUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    obj = await item_crud.get(session, item_id)
    if obj is None:
        raise not_found("plan_item", item_id)
    obj = await item_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="maintenance_plan_item", entity_id=obj.id, autocommit=True)
    return obj


# ── Day 4: planner endpoints ──────────────────────────────────────────────────

class GeneratePlanRequest(BaseModel):
    period_start: date_type
    period_end: date_type


class GeneratePlanResponse(BaseModel):
    schedule_id: int
    items_created: int
    brigades_assigned: int


@router.post("/maintenance/generate-plan", response_model=GeneratePlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_maintenance_plan(
    payload: GeneratePlanRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    """Auto-generate maintenance schedule for the given period from regulations."""
    from app.services.maintenance_planner import generate_plan

    result = await generate_plan(
        session,
        period_start=payload.period_start,
        period_end=payload.period_end,
        user_id=user.id,
    )
    return GeneratePlanResponse(
        schedule_id=result.schedule_id,
        items_created=result.items_created,
        brigades_assigned=result.brigades_assigned,
    )


@router.get("/maintenance/plan/{schedule_id}", response_model=List[MaintenancePlanItemResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_plan(
    schedule_id: int,
    session: AsyncSession = Depends(get_db),
):
    """List all plan items for a schedule."""
    rows = await session.execute(
        select(MaintenancePlanItem)
        .where(MaintenancePlanItem.schedule_id == schedule_id)
        .order_by(MaintenancePlanItem.planned_date)
    )
    return list(rows.scalars().all())


@router.get("/maintenance/upcoming", response_model=List[MaintenanceRegulationResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def upcoming_maintenance(
    days_ahead: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    """Regulations due within the next N days (default 7) — for reminders."""
    from app.services.maintenance_planner import get_upcoming_regulations

    return await get_upcoming_regulations(session, days_ahead=days_ahead)


@router.put("/maintenance/plan-item/{item_id}/approve", response_model=MaintenancePlanItemResponse)
async def approve_plan_item(
    item_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(MAINTENANCE_WRITE)),
):
    """Approve a maintenance plan item: create request + set status='approved'."""
    from app.services.maintenance_planner import approve_plan_item

    return await approve_plan_item(session, item_id=item_id, user_id=user.id)
