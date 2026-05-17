"""Планирование ТО."""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.boilers import Equipment
    from app.models.personnel import Brigade


# Тип ТО (ежемесячное, ежеквартальное и т.д.) с периодичностью в днях
class MaintenanceType(Base):
    __tablename__ = "maintenance_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    periodicity_days: Mapped[int] = mapped_column(nullable=False)

    regulations: Mapped[List["MaintenanceRegulation"]] = relationship(
        back_populates="maintenance_type", lazy="select"
    )
    plan_items: Mapped[List["MaintenancePlanItem"]] = relationship(
        back_populates="maintenance_type", lazy="select"
    )


# Регламент ТО: привязывает конкретное оборудование к виду обслуживания и дате
class MaintenanceRegulation(Base):
    __tablename__ = "maintenance_regulations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    maintenance_type_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_types.id"), nullable=False
    )
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_performed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    equipment: Mapped["Equipment"] = relationship(
        back_populates="regulations", lazy="selectin"
    )
    maintenance_type: Mapped["MaintenanceType"] = relationship(
        back_populates="regulations", lazy="selectin"
    )


# График ТО охватывает период (например, квартал) и содержит набор плановых позиций
class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    plan_items: Mapped[List["MaintenancePlanItem"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MaintenancePlanItem(Base):
    __tablename__ = "maintenance_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_schedules.id", ondelete="CASCADE"), nullable=False
    )
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    maintenance_type_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_types.id"), nullable=False
    )
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    assigned_brigade_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brigades.id")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    schedule: Mapped["MaintenanceSchedule"] = relationship(
        back_populates="plan_items", lazy="selectin"
    )
    equipment: Mapped["Equipment"] = relationship(lazy="selectin")
    maintenance_type: Mapped["MaintenanceType"] = relationship(
        back_populates="plan_items", lazy="selectin"
    )
    brigade: Mapped[Optional["Brigade"]] = relationship(lazy="selectin")
