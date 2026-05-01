"""Склад: материалы, остатки, движения, закупки."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.requests import WorkOrder


class MaterialCategory(Base):
    __tablename__ = "material_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    materials: Mapped[List["Material"]] = relationship(
        back_populates="category", lazy="select"
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("material_categories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    min_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, server_default="0"
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    category: Mapped["MaterialCategory"] = relationship(
        back_populates="materials", lazy="selectin"
    )
    stock_records: Mapped[List["MaterialStock"]] = relationship(
        back_populates="material", lazy="select"
    )
    movements: Mapped[List["MaterialMovement"]] = relationship(
        back_populates="material", lazy="select"
    )
    purchase_requests: Mapped[List["PurchaseRequest"]] = relationship(
        back_populates="material", lazy="select"
    )


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500))

    stock_records: Mapped[List["MaterialStock"]] = relationship(
        back_populates="warehouse", lazy="select"
    )


class MaterialStock(Base):
    __tablename__ = "material_stock"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, server_default="0"
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, server_default="0"
    )

    material: Mapped["Material"] = relationship(
        back_populates="stock_records", lazy="selectin"
    )
    warehouse: Mapped["Warehouse"] = relationship(
        back_populates="stock_records", lazy="selectin"
    )


class MaterialMovement(Base):
    __tablename__ = "material_movements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    work_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("work_orders.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )

    material: Mapped["Material"] = relationship(
        back_populates="movements", lazy="selectin"
    )
    warehouse: Mapped["Warehouse"] = relationship(lazy="selectin")
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        back_populates="material_movements", lazy="selectin"
    )


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )

    material: Mapped["Material"] = relationship(
        back_populates="purchase_requests", lazy="selectin"
    )
