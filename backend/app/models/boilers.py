"""Объекты учёта: котельные, оборудование, паспорта."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.maintenance import MaintenanceRegulation
    from app.models.requests import Request
    from app.models.telemetry import Telemetry, Threshold
    from app.models.ml import MLPrediction


class Boiler(Base):
    __tablename__ = "boilers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    commissioning_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    equipment: Mapped[List["Equipment"]] = relationship(
        back_populates="boiler", lazy="selectin"
    )
    telemetry: Mapped[List["Telemetry"]] = relationship(
        back_populates="boiler", lazy="select"
    )
    thresholds: Mapped[List["Threshold"]] = relationship(
        back_populates="boiler", lazy="selectin"
    )
    requests: Mapped[List["Request"]] = relationship(
        back_populates="boiler", lazy="select"
    )
    ml_predictions: Mapped[List["MLPrediction"]] = relationship(
        back_populates="boiler", lazy="select"
    )


class EquipmentCategory(Base):
    __tablename__ = "equipment_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    equipment: Mapped[List["Equipment"]] = relationship(
        back_populates="category", lazy="select"
    )


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    boiler_id: Mapped[int] = mapped_column(ForeignKey("boilers.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_categories.id"), nullable=False
    )
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200))
    installation_date: Mapped[date] = mapped_column(Date, nullable=False)
    warranty_until: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    boiler: Mapped["Boiler"] = relationship(back_populates="equipment", lazy="selectin")
    category: Mapped["EquipmentCategory"] = relationship(
        back_populates="equipment", lazy="selectin"
    )
    passport: Mapped[Optional["EquipmentPassport"]] = relationship(
        back_populates="equipment",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    regulations: Mapped[List["MaintenanceRegulation"]] = relationship(
        back_populates="equipment", lazy="select", cascade="all, delete-orphan"
    )


class EquipmentPassport(Base):
    __tablename__ = "equipment_passports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    passport_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-as-string
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )

    equipment: Mapped["Equipment"] = relationship(
        back_populates="passport", lazy="selectin"
    )
