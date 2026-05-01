"""Pydantic schemas: requests, work_orders, checklist, photos, acts."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


# -------- request_types -------------------------------------------------------
class RequestTypeBase(BaseModel):
    name: str = Field(max_length=100)


class RequestTypeCreate(RequestTypeBase):
    pass


class RequestTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)


class RequestTypeResponse(RequestTypeBase, OrmModel):
    id: int


# -------- request_priorities --------------------------------------------------
class RequestPriorityBase(BaseModel):
    name: str = Field(max_length=50)
    response_time_minutes: int = Field(gt=0)


class RequestPriorityCreate(RequestPriorityBase):
    pass


class RequestPriorityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    response_time_minutes: Optional[int] = Field(default=None, gt=0)


class RequestPriorityResponse(RequestPriorityBase, OrmModel):
    id: int


# -------- requests ------------------------------------------------------------
class RequestBase(BaseModel):
    number: str = Field(max_length=30)
    boiler_id: int
    type_id: int
    priority_id: int
    description: Optional[str] = Field(default=None, max_length=2000)
    source: str = Field(max_length=20)
    status: str = Field(max_length=30)


class RequestCreate(RequestBase):
    created_by: Optional[int] = None


class RequestUpdate(BaseModel):
    boiler_id: Optional[int] = None
    type_id: Optional[int] = None
    priority_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, max_length=30)
    closed_at: Optional[datetime] = None


class RequestResponse(RequestBase, OrmModel):
    id: int
    created_at: datetime
    created_by: Optional[int] = None
    closed_at: Optional[datetime] = None


# -------- work_orders ---------------------------------------------------------
class WorkOrderBase(BaseModel):
    request_id: int
    brigade_id: int
    status: str = Field(max_length=30)


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    brigade_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[str] = Field(default=None, max_length=30)


class WorkOrderResponse(WorkOrderBase, OrmModel):
    id: int
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# -------- work_order_checklist_items ------------------------------------------
class WorkOrderChecklistItemBase(BaseModel):
    work_order_id: int
    description: str = Field(max_length=1000)
    is_completed: bool = False
    sort_order: int = 0


class WorkOrderChecklistItemCreate(WorkOrderChecklistItemBase):
    pass


class WorkOrderChecklistItemUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=1000)
    is_completed: Optional[bool] = None
    sort_order: Optional[int] = None


class WorkOrderChecklistItemResponse(WorkOrderChecklistItemBase, OrmModel):
    id: int
    completed_at: Optional[datetime] = None


# -------- work_order_photos ---------------------------------------------------
class WorkOrderPhotoBase(BaseModel):
    work_order_id: int
    file_path: str = Field(max_length=1000)


class WorkOrderPhotoCreate(WorkOrderPhotoBase):
    pass


class WorkOrderPhotoResponse(WorkOrderPhotoBase, OrmModel):
    id: int
    uploaded_at: datetime


# -------- acts ----------------------------------------------------------------
class ActBase(BaseModel):
    work_order_id: int
    number: str = Field(max_length=30)
    total_amount: Decimal = Field(ge=0)
    pdf_path: Optional[str] = Field(default=None, max_length=1000)


class ActCreate(ActBase):
    pass


class ActUpdate(BaseModel):
    total_amount: Optional[Decimal] = Field(default=None, ge=0)
    pdf_path: Optional[str] = Field(default=None, max_length=1000)


class ActResponse(ActBase, OrmModel):
    id: int
    generated_at: datetime
