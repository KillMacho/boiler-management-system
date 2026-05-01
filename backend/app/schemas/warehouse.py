"""Pydantic schemas: warehouse, materials, stock, movements, purchase_requests."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


# -------- material_categories -------------------------------------------------
class MaterialCategoryBase(BaseModel):
    name: str = Field(max_length=100)


class MaterialCategoryCreate(MaterialCategoryBase):
    pass


class MaterialCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)


class MaterialCategoryResponse(MaterialCategoryBase, OrmModel):
    id: int


# -------- materials -----------------------------------------------------------
class MaterialBase(BaseModel):
    category_id: int
    name: str = Field(max_length=300)
    unit: str = Field(max_length=20)
    barcode: Optional[str] = Field(default=None, max_length=50)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)
    price: Decimal = Field(ge=0)


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=20)
    barcode: Optional[str] = Field(default=None, max_length=50)
    min_stock: Optional[Decimal] = Field(default=None, ge=0)
    price: Optional[Decimal] = Field(default=None, ge=0)


class MaterialResponse(MaterialBase, OrmModel):
    id: int


# -------- warehouses ----------------------------------------------------------
class WarehouseBase(BaseModel):
    name: str = Field(max_length=150)
    address: Optional[str] = Field(default=None, max_length=500)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    address: Optional[str] = Field(default=None, max_length=500)


class WarehouseResponse(WarehouseBase, OrmModel):
    id: int


# -------- material_stock ------------------------------------------------------
class MaterialStockBase(BaseModel):
    material_id: int
    warehouse_id: int
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    reserved_quantity: Decimal = Field(default=Decimal("0"), ge=0)


class MaterialStockCreate(MaterialStockBase):
    pass


class MaterialStockUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(default=None, ge=0)
    reserved_quantity: Optional[Decimal] = Field(default=None, ge=0)


class MaterialStockResponse(MaterialStockBase, OrmModel):
    id: int


# -------- material_movements --------------------------------------------------
class MaterialMovementBase(BaseModel):
    material_id: int
    warehouse_id: int
    movement_type: str = Field(max_length=20)
    quantity: Decimal = Field(gt=0)
    work_order_id: Optional[int] = None


class MaterialMovementCreate(MaterialMovementBase):
    pass


class MaterialMovementResponse(MaterialMovementBase, OrmModel):
    id: int
    created_at: datetime


# -------- purchase_requests ---------------------------------------------------
class PurchaseRequestBase(BaseModel):
    material_id: int
    quantity: Decimal = Field(gt=0)
    status: str = Field(max_length=30)


class PurchaseRequestCreate(PurchaseRequestBase):
    pass


class PurchaseRequestUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    status: Optional[str] = Field(default=None, max_length=30)


class PurchaseRequestResponse(PurchaseRequestBase, OrmModel):
    id: int
    created_at: datetime
