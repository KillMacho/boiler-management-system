"""Requests router: list/create/status-change with auto-classification."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.requests import Request, WorkOrder
from app.schemas.requests import RequestCreate, RequestResponse, WorkOrderResponse
from app.services import request_service
from app.services.permissions import READ_ANY, REQUEST_CREATE, REQUEST_WRITE
from app.utils.errors import not_found

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


class RequestCreatedResponse(BaseModel):
    request: RequestResponse
    work_order: Optional[WorkOrderResponse] = None
    warning: Optional[str] = Field(
        default=None, description="e.g. 'no_brigade_available'"
    )


class StatusChangePayload(BaseModel):
    status: str = Field(min_length=1, max_length=30)


@router.get("/", response_model=List[RequestResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_requests(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    type_id: Optional[int] = Query(None),
    priority_id: Optional[int] = Query(None),
    boiler_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Request)
    if status_filter:
        stmt = stmt.where(Request.status == status_filter)
    if type_id is not None:
        stmt = stmt.where(Request.type_id == type_id)
    if priority_id is not None:
        stmt = stmt.where(Request.priority_id == priority_id)
    if boiler_id is not None:
        stmt = stmt.where(Request.boiler_id == boiler_id)
    if source:
        stmt = stmt.where(Request.source == source)
    if date_from is not None:
        stmt = stmt.where(Request.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Request.created_at <= date_to)
    stmt = stmt.order_by(Request.created_at.desc()).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())


@router.get("/{request_id}", response_model=RequestResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_request(request_id: int, session: AsyncSession = Depends(get_db)):
    obj = await session.get(Request, request_id)
    if obj is None:
        raise not_found("request", request_id)
    return obj


@router.get("/{request_id}/work-order", response_model=Optional[WorkOrderResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_request_work_order(request_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(WorkOrder).where(WorkOrder.request_id == request_id).order_by(WorkOrder.id.desc()).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


@router.post("/", response_model=RequestCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_request_endpoint(
    payload: RequestCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(REQUEST_CREATE)),
):
    request, work_order, warning = await request_service.create_request(
        session, payload, user_id=user.id, source=payload.source
    )
    return RequestCreatedResponse(
        request=RequestResponse.model_validate(request),
        work_order=WorkOrderResponse.model_validate(work_order) if work_order else None,
        warning=warning,
    )


@router.put("/{request_id}/status", response_model=RequestResponse)
async def change_request_status(
    request_id: int,
    payload: StatusChangePayload = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(REQUEST_WRITE)),
):
    return await request_service.change_status(
        session, request_id=request_id, new_status=payload.status, user_id=user.id
    )
