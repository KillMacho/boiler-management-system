"""CRUD for warehouse: warehouses, materials, stock, movements, purchase_requests.
Also: reserve, write-off, receive, check-min-stock business operations.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.warehouse import (
    Material,
    MaterialCategory,
    MaterialMovement,
    MaterialStock,
    PurchaseRequest,
    Warehouse,
)
from app.schemas.warehouse import (
    MaterialCategoryCreate,
    MaterialCategoryResponse,
    MaterialCategoryUpdate,
    MaterialCreate,
    MaterialMovementCreate,
    MaterialMovementResponse,
    MaterialResponse,
    MaterialStockCreate,
    MaterialStockResponse,
    MaterialStockUpdate,
    MaterialUpdate,
    PurchaseRequestCreate,
    PurchaseRequestResponse,
    PurchaseRequestUpdate,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services import audit_service
from app.services.crud_base import CRUDBase
from app.services.permissions import READ_ANY, WAREHOUSE_WRITE
from app.utils.errors import not_found

router = APIRouter(prefix="/api/v1", tags=["warehouse"])

material_crud = CRUDBase[Material, MaterialCreate, MaterialUpdate](Material, soft_delete_status=None)
warehouse_crud = CRUDBase[Warehouse, WarehouseCreate, WarehouseUpdate](Warehouse, soft_delete_status=None)
mat_cat_crud = CRUDBase[MaterialCategory, MaterialCategoryCreate, MaterialCategoryUpdate](MaterialCategory, soft_delete_status=None)
stock_crud = CRUDBase[MaterialStock, MaterialStockCreate, MaterialStockUpdate](MaterialStock, soft_delete_status=None)
purchase_crud = CRUDBase[PurchaseRequest, PurchaseRequestCreate, PurchaseRequestUpdate](PurchaseRequest, soft_delete_status=None)


# ---------- material_categories --------------------------------------------
@router.get("/material-categories/", response_model=List[MaterialCategoryResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_material_categories(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await mat_cat_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/material-categories/", response_model=MaterialCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_material_category(
    payload: MaterialCategoryCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await mat_cat_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="material_category", entity_id=obj.id, autocommit=True)
    return obj


# ---------- materials ------------------------------------------------------
@router.get("/materials/", response_model=List[MaterialResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_materials(
    pagination: PaginationParams = Depends(get_pagination),
    category_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    extra = [Material.category_id == category_id] if category_id else []
    return await material_crud.list(session, skip=pagination.skip, limit=pagination.limit, extra_filters=extra)


@router.get("/materials/{material_id}", response_model=MaterialResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_material(material_id: int, session: AsyncSession = Depends(get_db)):
    obj = await material_crud.get(session, material_id)
    if obj is None:
        raise not_found("material", material_id)
    return obj


@router.post("/materials/", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await material_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="material", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: int,
    payload: MaterialUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await material_crud.get(session, material_id)
    if obj is None:
        raise not_found("material", material_id)
    obj = await material_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="material", entity_id=obj.id, autocommit=True)
    return obj


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await material_crud.get(session, material_id)
    if obj is None:
        raise not_found("material", material_id)
    await material_crud.hard_delete(session, obj)
    await audit_service.log(session, user_id=user.id, action="entity_hard_deleted", entity_type="material", entity_id=material_id, autocommit=True)


# ---------- warehouses -----------------------------------------------------
@router.get("/warehouses/", response_model=List[WarehouseResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_warehouses(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await warehouse_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/warehouses/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    payload: WarehouseCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await warehouse_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="warehouse", entity_id=obj.id, autocommit=True)
    return obj


# ---------- stock ----------------------------------------------------------
@router.get("/stock/", response_model=List[MaterialStockResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_stock(
    pagination: PaginationParams = Depends(get_pagination),
    material_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    extra = []
    if material_id is not None:
        extra.append(MaterialStock.material_id == material_id)
    if warehouse_id is not None:
        extra.append(MaterialStock.warehouse_id == warehouse_id)
    return await stock_crud.list(session, skip=pagination.skip, limit=pagination.limit, extra_filters=extra)


# ---------- movements ------------------------------------------------------
@router.get("/movements/", response_model=List[MaterialMovementResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_movements(
    pagination: PaginationParams = Depends(get_pagination),
    material_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    work_order_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(MaterialMovement)
    if material_id is not None:
        stmt = stmt.where(MaterialMovement.material_id == material_id)
    if warehouse_id is not None:
        stmt = stmt.where(MaterialMovement.warehouse_id == warehouse_id)
    if work_order_id is not None:
        stmt = stmt.where(MaterialMovement.work_order_id == work_order_id)
    stmt = stmt.order_by(MaterialMovement.created_at.desc()).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/movements/", response_model=MaterialMovementResponse, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: MaterialMovementCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = MaterialMovement(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="material_movement", entity_id=obj.id, autocommit=True)
    return obj


# ---------- purchase_requests ----------------------------------------------
@router.get("/purchase-requests/", response_model=List[PurchaseRequestResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_purchase_requests(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
):
    extra = [PurchaseRequest.status == status_filter] if status_filter else []
    return await purchase_crud.list(session, skip=pagination.skip, limit=pagination.limit, extra_filters=extra)


@router.post("/purchase-requests/", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_request(
    payload: PurchaseRequestCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await purchase_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="purchase_request", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/purchase-requests/{purchase_id}", response_model=PurchaseRequestResponse)
async def update_purchase_request(
    purchase_id: int,
    payload: PurchaseRequestUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    obj = await purchase_crud.get(session, purchase_id)
    if obj is None:
        raise not_found("purchase_request", purchase_id)
    obj = await purchase_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="purchase_request", entity_id=obj.id, autocommit=True)
    return obj


# ── Day 4: business operations ────────────────────────────────────────────────

class MaterialLineItemSchema(BaseModel):
    material_id: int
    quantity: Decimal = Field(gt=0)


class ReserveMaterialsRequest(BaseModel):
    work_order_id: int
    materials: List[MaterialLineItemSchema]


class ReserveMaterialsResponse(BaseModel):
    reserved_count: int
    purchase_requests_created: List[int]
    all_reserved: bool
    work_order_status: Optional[str] = None


class WriteMaterialsRequest(BaseModel):
    work_order_id: int
    materials: List[MaterialLineItemSchema]


class ReceiveMaterialRequest(BaseModel):
    material_id: int
    warehouse_id: int
    quantity: Decimal = Field(gt=0)
    purchase_request_id: Optional[int] = None


@router.post("/warehouse/reserve", response_model=ReserveMaterialsResponse)
async def reserve_materials(
    payload: ReserveMaterialsRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    """Reserve materials for a work order. Creates purchase requests for deficits."""
    from app.services.warehouse_service import MaterialLineItem, reserve_materials as svc_reserve
    from app.models.requests import WorkOrder

    items = [MaterialLineItem(m.material_id, m.quantity) for m in payload.materials]
    result = await svc_reserve(
        session, work_order_id=payload.work_order_id, materials=items, user_id=user.id
    )
    wo = await session.get(WorkOrder, payload.work_order_id)
    return ReserveMaterialsResponse(
        reserved_count=len(result.reserved),
        purchase_requests_created=result.purchase_requests_created,
        all_reserved=result.all_reserved,
        work_order_status=wo.status if wo else None,
    )


@router.post("/warehouse/write-off", response_model=List[MaterialMovementResponse])
async def write_off_materials(
    payload: WriteMaterialsRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    """Explicitly write off materials from stock for a work order."""
    from app.services.warehouse_service import MaterialLineItem, write_off_materials as svc_writeoff

    items = [MaterialLineItem(m.material_id, m.quantity) for m in payload.materials]
    movements = await svc_writeoff(
        session, work_order_id=payload.work_order_id, materials=items, user_id=user.id
    )
    for m in movements:
        await session.refresh(m)
    return movements


@router.post("/warehouse/receive", response_model=MaterialMovementResponse, status_code=status.HTTP_201_CREATED)
async def receive_materials(
    payload: ReceiveMaterialRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    """Receive materials into warehouse (income movement, optionally links purchase request)."""
    from app.services.warehouse_service import receive_materials as svc_receive

    return await svc_receive(
        session,
        material_id=payload.material_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        purchase_request_id=payload.purchase_request_id,
        user_id=user.id,
    )


@router.post("/warehouse/check-min-stock", response_model=List[PurchaseRequestResponse])
async def check_min_stock(
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WAREHOUSE_WRITE)),
):
    """Check all materials against minimum stock levels; create purchase requests for deficits."""
    from app.services.warehouse_service import check_min_stock_levels

    created = await check_min_stock_levels(session, user_id=user.id)
    return created
