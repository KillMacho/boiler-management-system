"""Pydantic schemas: maintenance types, regulations, schedules, plan items."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


class MaintenanceTypeBase(BaseModel):
    name: str = Field(max_length=100)
    periodicity_days: int = Field(gt=0)


class MaintenanceTypeCreate(MaintenanceTypeBase):
    pass


class MaintenanceTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    periodicity_days: Optional[int] = Field(default=None, gt=0)


class MaintenanceTypeResponse(MaintenanceTypeBase, OrmModel):
    id: int


class MaintenanceRegulationBase(BaseModel):
    equipment_id: int
    maintenance_type_id: int
    next_due_date: date
    last_performed_at: Optional[datetime] = None


class MaintenanceRegulationCreate(MaintenanceRegulationBase):
    pass


class MaintenanceRegulationUpdate(BaseModel):
    next_due_date: Optional[date] = None
    last_performed_at: Optional[datetime] = None


class MaintenanceRegulationResponse(MaintenanceRegulationBase, OrmModel):
    id: int


class MaintenanceScheduleBase(BaseModel):
    period_start: date
    period_end: date
    status: str = Field(max_length=30)


class MaintenanceScheduleCreate(MaintenanceScheduleBase):
    pass


class MaintenanceScheduleUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class MaintenanceScheduleResponse(MaintenanceScheduleBase, OrmModel):
    id: int
    created_at: datetime


class MaintenancePlanItemBase(BaseModel):
    schedule_id: int
    equipment_id: int
    maintenance_type_id: int
    planned_date: date
    assigned_brigade_id: Optional[int] = None
    status: str = Field(max_length=30)


class MaintenancePlanItemCreate(MaintenancePlanItemBase):
    pass


class MaintenancePlanItemUpdate(BaseModel):
    planned_date: Optional[date] = None
    assigned_brigade_id: Optional[int] = None
    status: Optional[str] = Field(default=None, max_length=30)


class MaintenancePlanItemResponse(MaintenancePlanItemBase, OrmModel):
    id: int
