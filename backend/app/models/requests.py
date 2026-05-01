"""Заявки и наряды."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.boilers import Boiler
    from app.models.personnel import Brigade, WorkTypeQualification
    from app.models.users import User
    from app.models.warehouse import MaterialMovement


class RequestType(Base):
    __tablename__ = "request_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    requests: Mapped[List["Request"]] = relationship(
        back_populates="request_type", lazy="select"
    )
    qualification_associations: Mapped[List["WorkTypeQualification"]] = relationship(
        back_populates="request_type",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RequestPriority(Base):
    __tablename__ = "request_priorities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    response_time_minutes: Mapped[int] = mapped_column(nullable=False)

    requests: Mapped[List["Request"]] = relationship(
        back_populates="priority", lazy="select"
    )


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    boiler_id: Mapped[int] = mapped_column(ForeignKey("boilers.id"), nullable=False)
    type_id: Mapped[int] = mapped_column(ForeignKey("request_types.id"), nullable=False)
    priority_id: Mapped[int] = mapped_column(
        ForeignKey("request_priorities.id"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(2000))
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    boiler: Mapped["Boiler"] = relationship(back_populates="requests", lazy="selectin")
    request_type: Mapped["RequestType"] = relationship(
        back_populates="requests", lazy="selectin"
    )
    priority: Mapped["RequestPriority"] = relationship(
        back_populates="requests", lazy="selectin"
    )
    creator: Mapped[Optional["User"]] = relationship(lazy="selectin")
    work_orders: Mapped[List["WorkOrder"]] = relationship(
        back_populates="request", lazy="select"
    )


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False)
    brigade_id: Mapped[int] = mapped_column(ForeignKey("brigades.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    request: Mapped["Request"] = relationship(
        back_populates="work_orders", lazy="selectin"
    )
    brigade: Mapped["Brigade"] = relationship(
        back_populates="work_orders", lazy="selectin"
    )
    checklist_items: Mapped[List["WorkOrderChecklistItem"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    photos: Mapped[List["WorkOrderPhoto"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        lazy="select",
    )
    act: Mapped[Optional["Act"]] = relationship(
        back_populates="work_order", uselist=False, lazy="selectin"
    )
    material_movements: Mapped[List["MaterialMovement"]] = relationship(
        back_populates="work_order", lazy="select"
    )


class WorkOrderChecklistItem(Base):
    __tablename__ = "work_order_checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")

    work_order: Mapped["WorkOrder"] = relationship(
        back_populates="checklist_items", lazy="selectin"
    )


class WorkOrderPhoto(Base):
    __tablename__ = "work_order_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )

    work_order: Mapped["WorkOrder"] = relationship(
        back_populates="photos", lazy="selectin"
    )


class Act(Base):
    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id"), nullable=False, unique=True
    )
    number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1000))

    work_order: Mapped["WorkOrder"] = relationship(
        back_populates="act", lazy="selectin"
    )
