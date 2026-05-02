"""CRUD for customers."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.customers import Customer
from app.schemas.customers import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services import audit_service
from app.services.crud_base import CRUDBase
from app.services.permissions import CUSTOMER_WRITE, READ_ANY
from app.utils.errors import not_found

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])
crud = CRUDBase[Customer, CustomerCreate, CustomerUpdate](Customer, soft_delete_status=None)


@router.get("/", response_model=List[CustomerResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_customers(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/{customer_id}", response_model=CustomerResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_customer(customer_id: int, session: AsyncSession = Depends(get_db)):
    obj = await crud.get(session, customer_id)
    if obj is None:
        raise not_found("customer", customer_id)
    return obj


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(CUSTOMER_WRITE)),
):
    obj = await crud.create(session, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_created",
        entity_type="customer", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(CUSTOMER_WRITE)),
):
    obj = await crud.get(session, customer_id)
    if obj is None:
        raise not_found("customer", customer_id)
    obj = await crud.update(session, obj, payload)
    await audit_service.log(
        session, user_id=user.id, action="entity_updated",
        entity_type="customer", entity_id=obj.id, autocommit=True,
    )
    return obj


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(CUSTOMER_WRITE)),
):
    obj = await crud.get(session, customer_id)
    if obj is None:
        raise not_found("customer", customer_id)
    await crud.hard_delete(session, obj)
    await audit_service.log(
        session, user_id=user.id, action="entity_hard_deleted",
        entity_type="customer", entity_id=customer_id, autocommit=True,
    )
