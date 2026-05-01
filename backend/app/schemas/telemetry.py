"""Pydantic schemas: telemetry, thresholds."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


class TelemetryBase(BaseModel):
    boiler_id: int
    timestamp: datetime
    temperature_heat: Optional[Decimal] = None
    pressure: Optional[Decimal] = None
    co_level: Optional[Decimal] = None
    gas_flow: Optional[Decimal] = None
    water_level: Optional[Decimal] = None
    temperature_return: Optional[Decimal] = None
    furnace_draft: Optional[Decimal] = None
    status: str = Field(max_length=20)


class TelemetryCreate(TelemetryBase):
    pass


class TelemetryUpdate(BaseModel):
    temperature_heat: Optional[Decimal] = None
    pressure: Optional[Decimal] = None
    co_level: Optional[Decimal] = None
    gas_flow: Optional[Decimal] = None
    water_level: Optional[Decimal] = None
    temperature_return: Optional[Decimal] = None
    furnace_draft: Optional[Decimal] = None
    status: Optional[str] = Field(default=None, max_length=20)


class TelemetryResponse(TelemetryBase, OrmModel):
    id: int


class ThresholdBase(BaseModel):
    boiler_id: Optional[int] = None
    parameter_name: str = Field(max_length=50)
    min_warning: Optional[Decimal] = None
    max_warning: Optional[Decimal] = None
    min_critical: Optional[Decimal] = None
    max_critical: Optional[Decimal] = None


class ThresholdCreate(ThresholdBase):
    pass


class ThresholdUpdate(BaseModel):
    boiler_id: Optional[int] = None
    parameter_name: Optional[str] = Field(default=None, max_length=50)
    min_warning: Optional[Decimal] = None
    max_warning: Optional[Decimal] = None
    min_critical: Optional[Decimal] = None
    max_critical: Optional[Decimal] = None


class ThresholdResponse(ThresholdBase, OrmModel):
    id: int
