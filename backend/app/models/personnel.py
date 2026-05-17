"""Персонал: подразделения, должности, сотрудники, бригады, табель."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.requests import RequestType, WorkOrder
    from app.models.users import User


# Подразделение (отдел) — справочник для группировки сотрудников
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    employees: Mapped[List["Employee"]] = relationship(
        back_populates="department", lazy="select"
    )


# Должность содержит базовый оклад, используемый при расчёте зарплаты
class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    employees: Mapped[List["Employee"]] = relationship(
        back_populates="position", lazy="select"
    )


class Qualification(Base):
    __tablename__ = "qualifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    employee_associations: Mapped[List["EmployeeQualification"]] = relationship(
        back_populates="qualification", lazy="select"
    )
    work_type_associations: Mapped[List["WorkTypeQualification"]] = relationship(
        back_populates="qualification", lazy="select"
    )


# Сотрудник — центральная HR-сущность; связан с пользователем, бригадой, табелем
class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    employee_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=False
    )
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    department: Mapped["Department"] = relationship(
        back_populates="employees", lazy="selectin"
    )
    position: Mapped["Position"] = relationship(
        back_populates="employees", lazy="selectin"
    )
    contact: Mapped[Optional["EmployeeContact"]] = relationship(
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    qualification_associations: Mapped[List["EmployeeQualification"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan", lazy="selectin"
    )
    brigade_memberships: Mapped[List["BrigadeMember"]] = relationship(
        back_populates="employee", lazy="select"
    )
    led_brigades: Mapped[List["Brigade"]] = relationship(
        back_populates="leader",
        foreign_keys="Brigade.leader_employee_id",
        lazy="select",
    )
    timesheets: Mapped[List["Timesheet"]] = relationship(
        back_populates="employee", lazy="select"
    )
    users: Mapped[List["User"]] = relationship(
        back_populates="employee", lazy="select"
    )


# Контактные данные хранятся отдельно — 1-to-1 с CASCADE delete
class EmployeeContact(Base):
    __tablename__ = "employee_contacts"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0"
    )
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="1"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="contact", lazy="selectin"
    )


class EmployeeQualification(Base):
    __tablename__ = "employee_qualifications"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True
    )
    qualification_id: Mapped[int] = mapped_column(
        ForeignKey("qualifications.id"), primary_key=True
    )
    grade: Mapped[Optional[int]] = mapped_column(SmallInteger)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)

    employee: Mapped["Employee"] = relationship(
        back_populates="qualification_associations", lazy="selectin"
    )
    qualification: Mapped["Qualification"] = relationship(
        back_populates="employee_associations", lazy="selectin"
    )


# Бригада объединяет сотрудников для выполнения нарядов; у неё есть бригадир
class Brigade(Base):
    __tablename__ = "brigades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    leader_employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    leader: Mapped[Optional["Employee"]] = relationship(
        back_populates="led_brigades",
        foreign_keys=[leader_employee_id],
        lazy="selectin",
    )
    members: Mapped[List["BrigadeMember"]] = relationship(
        back_populates="brigade",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    work_orders: Mapped[List["WorkOrder"]] = relationship(
        back_populates="brigade", lazy="select"
    )


class BrigadeMember(Base):
    __tablename__ = "brigade_members"

    brigade_id: Mapped[int] = mapped_column(
        ForeignKey("brigades.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), primary_key=True
    )
    joined_date: Mapped[date] = mapped_column(Date, nullable=False)

    brigade: Mapped["Brigade"] = relationship(back_populates="members", lazy="selectin")
    employee: Mapped["Employee"] = relationship(
        back_populates="brigade_memberships", lazy="selectin"
    )


# Связывает тип заявки с необходимыми квалификациями — используется при назначении бригады
class WorkTypeQualification(Base):
    __tablename__ = "work_type_qualifications"

    request_type_id: Mapped[int] = mapped_column(
        ForeignKey("request_types.id", ondelete="CASCADE"), primary_key=True
    )
    qualification_id: Mapped[int] = mapped_column(
        ForeignKey("qualifications.id"), primary_key=True
    )

    request_type: Mapped["RequestType"] = relationship(
        back_populates="qualification_associations", lazy="selectin"
    )
    qualification: Mapped["Qualification"] = relationship(
        back_populates="work_type_associations", lazy="selectin"
    )


# Строка табеля учёта рабочего времени: тип часов (regular/overtime/vacation/sick)
class Timesheet(Base):
    __tablename__ = "timesheets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column("date", Date, nullable=False)
    hours_worked: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    hours_type: Mapped[str] = mapped_column(String(20), nullable=False)

    employee: Mapped["Employee"] = relationship(
        back_populates="timesheets", lazy="selectin"
    )
