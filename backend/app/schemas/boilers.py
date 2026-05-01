"""Pydantic schemas for boilers, equipment, equipment_passports, equipment_categories."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


# -------- equipment_categories -------------------------------------------------
class EquipmentCategoryBase(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class EquipmentCategoryCreate(EquipmentCategoryBase):
    pass


class EquipmentCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class EquipmentCategoryResponse(EquipmentCategoryBase, OrmModel):
    id: int


# -------- boilers --------------------------------------------------------------
class BoilerBase(BaseModel):
    name: str = Field(max_length=200)
    address: str = Field(max_length=500)
    latitude: Decimal
    longitude: Decimal
    commissioning_date: date
    status: str = Field(max_length=30)


class BoilerCreate(BoilerBase):
    pass


class BoilerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    commissioning_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class BoilerResponse(BoilerBase, OrmModel):
    id: int


# -------- equipment ------------------------------------------------------------
class EquipmentBase(BaseModel):
    boiler_id: int
    category_id: int
    serial_number: str = Field(max_length=100)
    model: str = Field(max_length=200)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    installation_date: date
    warranty_until: Optional[date] = None
    status: str = Field(max_length=30)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    boiler_id: Optional[int] = None
    category_id: Optional[int] = None
    serial_number: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=200)
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    installation_date: Optional[date] = None
    warranty_until: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class EquipmentResponse(EquipmentBase, OrmModel):
    id: int


# -------- equipment_passports --------------------------------------------------
class EquipmentPassportBase(BaseModel):
    equipment_id: int
    passport_data: str  # JSON string


class EquipmentPassportCreate(EquipmentPassportBase):
    pass


class EquipmentPassportUpdate(BaseModel):
    passport_data: Optional[str] = None


class EquipmentPassportResponse(EquipmentPassportBase, OrmModel):
    id: int
    created_at: datetime
