"""Read-only lookup tables for UI dropdowns."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.boilers import EquipmentCategory
from app.models.maintenance import MaintenanceType
from app.models.personnel import Qualification
from app.models.requests import RequestPriority, RequestType
from app.models.users import Role
from app.models.warehouse import MaterialCategory
from app.schemas.boilers import EquipmentCategoryResponse
from app.schemas.maintenance import MaintenanceTypeResponse
from app.schemas.personnel import QualificationResponse
from app.schemas.requests import RequestPriorityResponse, RequestTypeResponse
from app.schemas.users import RoleResponse
from app.schemas.warehouse import MaterialCategoryResponse
from app.services.permissions import READ_ANY

router = APIRouter(
    prefix="/api/v1/lookups",
    tags=["lookups"],
    dependencies=[Depends(RoleChecker(READ_ANY))],
)


async def _list_all(session: AsyncSession, model):
    return list((await session.execute(select(model).order_by(model.id))).scalars().all())


@router.get("/equipment-categories", response_model=List[EquipmentCategoryResponse])
async def list_equipment_categories(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, EquipmentCategory)


@router.get("/request-types", response_model=List[RequestTypeResponse])
async def list_request_types(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, RequestType)


@router.get("/request-priorities", response_model=List[RequestPriorityResponse])
async def list_request_priorities(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, RequestPriority)


@router.get("/maintenance-types", response_model=List[MaintenanceTypeResponse])
async def list_maintenance_types(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, MaintenanceType)


@router.get("/material-categories", response_model=List[MaterialCategoryResponse])
async def list_material_categories(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, MaterialCategory)


@router.get("/qualifications", response_model=List[QualificationResponse])
async def list_qualifications(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, Qualification)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(session: AsyncSession = Depends(get_db)):
    return await _list_all(session, Role)
