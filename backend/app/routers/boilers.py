"""CRUD: boilers + equipment + equipment_passports."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_include_deleted, get_pagination
from app.models.boilers import Boiler, Equipment, EquipmentPassport
from app.schemas.boilers import (
    BoilerCreate,
    BoilerResponse,
    BoilerUpdate,
    EquipmentCreate,
    EquipmentPassportCreate,
    EquipmentPassportResponse,
    EquipmentPassportUpdate,
    EquipmentResponse,
    EquipmentUpdate,
)
from app.services import audit_service
from app.services.crud_base import CRUDBase
from app.services.permissions import BOILER_WRITE, READ_ANY
from app.utils.errors import conflict, not_found

router = APIRouter(prefix="/api/v1", tags=["boilers"])

boiler_crud = CRUDBase[Boiler, BoilerCreate, BoilerUpdate](
    Boiler, soft_delete_status="decommissioned"
)
equipment_crud = CRUDBase[Equipment, EquipmentCreate, EquipmentUpdate](
    Equipment, soft_delete_status="decommissioned"
)


# ---------- boilers ---------------------------------------------------------
@router.get("/boilers/", response_model=List[BoilerResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_boilers(
    pagination: PaginationParams = Depends(get_pagination),
    include_deleted: bool = Depends(get_include_deleted),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
):
    extra = []
    if status_filter:
        extra.append(Boiler.status == status_filter)
    return await boiler_crud.list(
        session,
        skip=pagination.skip,
        limit=pagination.limit,
        include_deleted=include_deleted,
        extra_filters=extra,
    )


@router.get("/boilers/{boiler_id}", response_model=BoilerResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_boiler(boiler_id: int, session: AsyncSession = Depends(get_db)):
    obj = await boiler_crud.get(session, boiler_id)
    if obj is None:
        raise not_found("boiler", boiler_id)
    return obj


@router.post("/boilers/", response_model=BoilerResponse, status_code=status.HTTP_201_CREATED)
async def create_boiler(
    payload: BoilerCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await boiler_crud.create(session, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_created",
        entity_type="boiler", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.put("/boilers/{boiler_id}", response_model=BoilerResponse)
async def update_boiler(
    boiler_id: int,
    payload: BoilerUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await boiler_crud.get(session, boiler_id)
    if obj is None:
        raise not_found("boiler", boiler_id)
    obj = await boiler_crud.update(session, obj, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_updated",
        entity_type="boiler", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.delete("/boilers/{boiler_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_boiler(
    boiler_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await boiler_crud.get(session, boiler_id)
    if obj is None:
        raise not_found("boiler", boiler_id)
    if obj.status == "decommissioned":
        raise not_found("boiler", boiler_id)
    await boiler_crud.soft_delete(session, obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_soft_deleted",
        entity_type="boiler", entity_id=boiler_id, autocommit=True,
    )


@router.get(
    "/boilers/{boiler_id}/equipment",
    response_model=List[EquipmentResponse],
    dependencies=[Depends(RoleChecker(READ_ANY))],
)
async def list_boiler_equipment(
    boiler_id: int,
    include_deleted: bool = Depends(get_include_deleted),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Equipment).where(Equipment.boiler_id == boiler_id)
    if not include_deleted:
        stmt = stmt.where(Equipment.status != "decommissioned")
    return list((await session.execute(stmt.order_by(Equipment.id))).scalars().all())


# ---------- equipment -------------------------------------------------------
@router.get("/equipment/", response_model=List[EquipmentResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_equipment(
    pagination: PaginationParams = Depends(get_pagination),
    include_deleted: bool = Depends(get_include_deleted),
    boiler_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    extra = []
    if boiler_id is not None:
        extra.append(Equipment.boiler_id == boiler_id)
    if category_id is not None:
        extra.append(Equipment.category_id == category_id)
    return await equipment_crud.list(
        session,
        skip=pagination.skip,
        limit=pagination.limit,
        include_deleted=include_deleted,
        extra_filters=extra,
    )


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_equipment(equipment_id: int, session: AsyncSession = Depends(get_db)):
    obj = await equipment_crud.get(session, equipment_id)
    if obj is None:
        raise not_found("equipment", equipment_id)
    return obj


@router.post("/equipment/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    payload: EquipmentCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await equipment_crud.create(session, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_created",
        entity_type="equipment", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await equipment_crud.get(session, equipment_id)
    if obj is None:
        raise not_found("equipment", equipment_id)
    obj = await equipment_crud.update(session, obj, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_updated",
        entity_type="equipment", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    obj = await equipment_crud.get(session, equipment_id)
    if obj is None or obj.status == "decommissioned":
        raise not_found("equipment", equipment_id)
    await equipment_crud.soft_delete(session, obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_soft_deleted",
        entity_type="equipment", entity_id=equipment_id, autocommit=True,
    )


# ---------- equipment_passports --------------------------------------------
@router.get(
    "/equipment/{equipment_id}/passport",
    response_model=EquipmentPassportResponse,
    dependencies=[Depends(RoleChecker(READ_ANY))],
)
async def get_passport(equipment_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(EquipmentPassport).where(EquipmentPassport.equipment_id == equipment_id)
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise not_found("passport for equipment", equipment_id)
    return obj


@router.post(
    "/equipment/{equipment_id}/passport",
    response_model=EquipmentPassportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_passport(
    equipment_id: int,
    payload: EquipmentPassportCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    if payload.equipment_id != equipment_id:
        raise conflict("payload.equipment_id mismatch with URL")
    existing = (await session.execute(
        select(EquipmentPassport).where(EquipmentPassport.equipment_id == equipment_id)
    )).scalar_one_or_none()
    if existing is not None:
        raise conflict("passport already exists for this equipment")
    obj = EquipmentPassport(equipment_id=equipment_id, passport_data=payload.passport_data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_created",
        entity_type="equipment_passport", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.put(
    "/equipment/{equipment_id}/passport",
    response_model=EquipmentPassportResponse,
)
async def update_passport(
    equipment_id: int,
    payload: EquipmentPassportUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(BOILER_WRITE)),
):
    stmt = select(EquipmentPassport).where(EquipmentPassport.equipment_id == equipment_id)
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise not_found("passport for equipment", equipment_id)
    if payload.passport_data is not None:
        obj.passport_data = payload.passport_data
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_updated",
        entity_type="equipment_passport", entity_id=obj.id, autocommit=True,
    )
    return obj
