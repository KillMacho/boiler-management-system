"""Pydantic schemas: personnel (departments, positions, employees, brigades, qualifications, timesheets)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import OrmModel


# -------- departments ---------------------------------------------------------
class DepartmentBase(BaseModel):
    name: str = Field(max_length=150)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)


class DepartmentResponse(DepartmentBase, OrmModel):
    id: int


# -------- positions -----------------------------------------------------------
class PositionBase(BaseModel):
    name: str = Field(max_length=150)
    base_salary: Decimal = Field(ge=0)


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    base_salary: Optional[Decimal] = Field(default=None, ge=0)


class PositionResponse(PositionBase, OrmModel):
    id: int


# -------- qualifications ------------------------------------------------------
class QualificationBase(BaseModel):
    name: str = Field(max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)


class QualificationCreate(QualificationBase):
    pass


class QualificationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)


class QualificationResponse(QualificationBase, OrmModel):
    id: int


# -------- employees -----------------------------------------------------------
class EmployeeBase(BaseModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    middle_name: Optional[str] = Field(default=None, max_length=100)
    employee_number: str = Field(max_length=20)
    department_id: int
    position_id: int
    hire_date: date
    status: str = Field(max_length=30)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    middle_name: Optional[str] = Field(default=None, max_length=100)
    employee_number: Optional[str] = Field(default=None, max_length=20)
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    hire_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class EmployeeResponse(EmployeeBase, OrmModel):
    id: int


# -------- employee_contacts ---------------------------------------------------
class EmployeeContactBase(BaseModel):
    employee_id: int
    email: EmailStr
    email_verified: bool = False
    email_notifications_enabled: bool = True


class EmployeeContactCreate(EmployeeContactBase):
    pass


class EmployeeContactUpdate(BaseModel):
    email: Optional[EmailStr] = None
    email_verified: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None


class EmployeeContactResponse(EmployeeContactBase, OrmModel):
    last_updated: datetime


# -------- employee_qualifications (junction) ---------------------------------
class EmployeeQualificationBase(BaseModel):
    employee_id: int
    qualification_id: int
    grade: Optional[int] = Field(default=None, ge=1, le=10)
    assigned_date: date


class EmployeeQualificationCreate(EmployeeQualificationBase):
    pass


class EmployeeQualificationResponse(EmployeeQualificationBase, OrmModel):
    pass


# -------- brigades ------------------------------------------------------------
class BrigadeBase(BaseModel):
    name: str = Field(max_length=150)
    leader_employee_id: Optional[int] = None
    status: str = Field(max_length=30)


class BrigadeCreate(BrigadeBase):
    pass


class BrigadeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    leader_employee_id: Optional[int] = None
    status: Optional[str] = Field(default=None, max_length=30)


class BrigadeResponse(BrigadeBase, OrmModel):
    id: int


# -------- brigade_members (junction) -----------------------------------------
class BrigadeMemberBase(BaseModel):
    brigade_id: int
    employee_id: int
    joined_date: date


class BrigadeMemberCreate(BrigadeMemberBase):
    pass


class BrigadeMemberResponse(BrigadeMemberBase, OrmModel):
    pass


# -------- work_type_qualifications (junction) -------------------------------
class WorkTypeQualificationBase(BaseModel):
    request_type_id: int
    qualification_id: int


class WorkTypeQualificationCreate(WorkTypeQualificationBase):
    pass


class WorkTypeQualificationResponse(WorkTypeQualificationBase, OrmModel):
    pass


# -------- timesheets ----------------------------------------------------------
class TimesheetBase(BaseModel):
    employee_id: int
    date: date
    hours_worked: Decimal = Field(ge=0, le=24)
    hours_type: str = Field(max_length=20)


class TimesheetCreate(TimesheetBase):
    pass


class TimesheetUpdate(BaseModel):
    hours_worked: Optional[Decimal] = Field(default=None, ge=0, le=24)
    hours_type: Optional[str] = Field(default=None, max_length=20)


class TimesheetResponse(TimesheetBase, OrmModel):
    id: int
