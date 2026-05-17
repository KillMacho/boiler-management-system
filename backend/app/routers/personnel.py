"""CRUD for personnel: employees, brigades+members, qualifications, departments, positions, timesheets.
Also: free brigades, brigade qualifications, timesheet business operations.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_include_deleted, get_pagination
from app.models.personnel import (
    Brigade,
    BrigadeMember,
    Department,
    Employee,
    EmployeeContact,
    Position,
    Qualification,
    Timesheet,
)
from app.schemas.personnel import (
    BrigadeCreate,
    BrigadeMemberCreate,
    BrigadeMemberResponse,
    BrigadeResponse,
    BrigadeUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    EmployeeContactCreate,
    EmployeeContactResponse,
    EmployeeContactUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
    QualificationCreate,
    QualificationResponse,
    QualificationUpdate,
    TimesheetCreate,
    TimesheetResponse,
    TimesheetUpdate,
)
from app.services import audit_service
from app.services.crud_base import CRUDBase
from app.services.permissions import HR_WRITE, READ_ANY
from app.utils.errors import conflict, not_found

router = APIRouter(prefix="/api/v1", tags=["personnel"])

# Сотрудники и бригады используют мягкое удаление (terminated / inactive)
employee_crud = CRUDBase[Employee, EmployeeCreate, EmployeeUpdate](Employee, soft_delete_status="terminated")
brigade_crud = CRUDBase[Brigade, BrigadeCreate, BrigadeUpdate](Brigade, soft_delete_status="inactive")
department_crud = CRUDBase[Department, DepartmentCreate, DepartmentUpdate](Department, soft_delete_status=None)
position_crud = CRUDBase[Position, PositionCreate, PositionUpdate](Position, soft_delete_status=None)
qualification_crud = CRUDBase[Qualification, QualificationCreate, QualificationUpdate](Qualification, soft_delete_status=None)


# ---------- employees ------------------------------------------------------
@router.get("/employees/", response_model=List[EmployeeResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_employees(
    pagination: PaginationParams = Depends(get_pagination),
    include_deleted: bool = Depends(get_include_deleted),
    department_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
):
    extra = []
    if department_id is not None:
        extra.append(Employee.department_id == department_id)
    if status_filter:
        extra.append(Employee.status == status_filter)
    return await employee_crud.list(
        session, skip=pagination.skip, limit=pagination.limit,
        include_deleted=include_deleted, extra_filters=extra,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_employee(employee_id: int, session: AsyncSession = Depends(get_db)):
    obj = await employee_crud.get(session, employee_id)
    if obj is None:
        raise not_found("employee", employee_id)
    return obj


@router.post("/employees/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await employee_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="employee", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await employee_crud.get(session, employee_id)
    if obj is None:
        raise not_found("employee", employee_id)
    obj = await employee_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="employee", entity_id=obj.id, autocommit=True)
    return obj


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await employee_crud.get(session, employee_id)
    if obj is None or obj.status == "terminated":
        raise not_found("employee", employee_id)
    await employee_crud.soft_delete(session, obj)
    await audit_service.log(session, user_id=user.id, action="entity_soft_deleted", entity_type="employee", entity_id=employee_id, autocommit=True)


# ---------- employee_contacts ---------------------------------------------
@router.get("/employees/{employee_id}/contact", response_model=EmployeeContactResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_employee_contact(employee_id: int, session: AsyncSession = Depends(get_db)):
    obj = await session.get(EmployeeContact, employee_id)
    if obj is None:
        raise not_found("employee_contact", employee_id)
    return obj


@router.put("/employees/{employee_id}/contact", response_model=EmployeeContactResponse)
async def upsert_employee_contact(
    employee_id: int,
    payload: EmployeeContactUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await session.get(EmployeeContact, employee_id)
    if obj is None:
        if payload.email is None:
            raise conflict("email is required for first creation")
        obj = EmployeeContact(employee_id=employee_id, email=payload.email,
                              email_verified=payload.email_verified or False,
                              email_notifications_enabled=payload.email_notifications_enabled
                              if payload.email_notifications_enabled is not None else True)
        session.add(obj)
    else:
        for f, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, f, v)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="employee_contact", entity_id=employee_id, autocommit=True)
    return obj


# ---------- brigades -------------------------------------------------------
@router.get("/brigades/", response_model=List[BrigadeResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_brigades(
    pagination: PaginationParams = Depends(get_pagination),
    include_deleted: bool = Depends(get_include_deleted),
    session: AsyncSession = Depends(get_db),
):
    return await brigade_crud.list(
        session, skip=pagination.skip, limit=pagination.limit,
        include_deleted=include_deleted,
    )


# Маршрут /free должен быть ВЫШЕ /{brigade_id}, иначе FastAPI примет "free" за целое число
@router.get("/brigades/free", response_model=List[BrigadeResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_free_brigades(session: AsyncSession = Depends(get_db)):
    """Return brigades that are active and have no assigned/in_progress work orders."""
    from app.models.requests import WorkOrder
    from sqlalchemy import select as sa_select

    busy_subq = (
        sa_select(WorkOrder.brigade_id)
        .where(WorkOrder.status.in_(["assigned", "in_progress"]))
        .scalar_subquery()
    )
    rows = await session.execute(
        sa_select(Brigade)
        .where(Brigade.status != "inactive")
        .where(~Brigade.id.in_(busy_subq))
        .order_by(Brigade.id)
    )
    return list(rows.scalars().all())


@router.get("/brigades/{brigade_id}", response_model=BrigadeResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_brigade(brigade_id: int, session: AsyncSession = Depends(get_db)):
    obj = await brigade_crud.get(session, brigade_id)
    if obj is None:
        raise not_found("brigade", brigade_id)
    return obj


@router.post("/brigades/", response_model=BrigadeResponse, status_code=status.HTTP_201_CREATED)
async def create_brigade(
    payload: BrigadeCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await brigade_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="brigade", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/brigades/{brigade_id}", response_model=BrigadeResponse)
async def update_brigade(
    brigade_id: int,
    payload: BrigadeUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await brigade_crud.get(session, brigade_id)
    if obj is None:
        raise not_found("brigade", brigade_id)
    obj = await brigade_crud.update(session, obj, payload)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="brigade", entity_id=obj.id, autocommit=True)
    return obj


@router.delete("/brigades/{brigade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brigade(
    brigade_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await brigade_crud.get(session, brigade_id)
    if obj is None or obj.status == "inactive":
        raise not_found("brigade", brigade_id)
    await brigade_crud.soft_delete(session, obj)
    await audit_service.log(session, user_id=user.id, action="entity_soft_deleted", entity_type="brigade", entity_id=brigade_id, autocommit=True)


# ---------- brigade_members (junction, hard delete) -----------------------
@router.get("/brigades/{brigade_id}/members", response_model=List[BrigadeMemberResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_brigade_members(brigade_id: int, session: AsyncSession = Depends(get_db)):
    stmt = select(BrigadeMember).where(BrigadeMember.brigade_id == brigade_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/brigades/{brigade_id}/members", response_model=BrigadeMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_brigade_member(
    brigade_id: int,
    payload: BrigadeMemberCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    if payload.brigade_id != brigade_id:
        raise conflict("brigade_id mismatch")
    obj = BrigadeMember(brigade_id=brigade_id, employee_id=payload.employee_id,
                        joined_date=payload.joined_date or date_type.today())
    session.add(obj)
    await session.commit()
    await audit_service.log(session, user_id=user.id, action="brigade_member_added",
                             entity_type="brigade", entity_id=brigade_id,
                             details={"employee_id": payload.employee_id}, autocommit=True)
    return obj


@router.delete("/brigades/{brigade_id}/members/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_brigade_member(
    brigade_id: int,
    employee_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    stmt = select(BrigadeMember).where(
        BrigadeMember.brigade_id == brigade_id,
        BrigadeMember.employee_id == employee_id,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise not_found("brigade_member", f"{brigade_id}/{employee_id}")
    await session.delete(obj)
    await session.commit()
    await audit_service.log(session, user_id=user.id, action="brigade_member_removed",
                             entity_type="brigade", entity_id=brigade_id,
                             details={"employee_id": employee_id}, autocommit=True)


# ---------- qualifications -------------------------------------------------
@router.get("/qualifications/", response_model=List[QualificationResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_qualifications(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await qualification_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/qualifications/", response_model=QualificationResponse, status_code=status.HTTP_201_CREATED)
async def create_qualification(
    payload: QualificationCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await qualification_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="qualification", entity_id=obj.id, autocommit=True)
    return obj


# ---------- departments ----------------------------------------------------
@router.get("/departments/", response_model=List[DepartmentResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_departments(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await department_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/departments/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await department_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="department", entity_id=obj.id, autocommit=True)
    return obj


# ---------- positions ------------------------------------------------------
@router.get("/positions/", response_model=List[PositionResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_positions(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
):
    return await position_crud.list(session, skip=pagination.skip, limit=pagination.limit)


@router.post("/positions/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    payload: PositionCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await position_crud.create(session, payload)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="position", entity_id=obj.id, autocommit=True)
    return obj


# ---------- timesheets -----------------------------------------------------
@router.get("/timesheets/", response_model=List[TimesheetResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_timesheets(
    pagination: PaginationParams = Depends(get_pagination),
    employee_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Timesheet)
    if employee_id is not None:
        stmt = stmt.where(Timesheet.employee_id == employee_id)
    stmt = stmt.order_by(Timesheet.date.desc()).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/timesheets/", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
    payload: TimesheetCreate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = Timesheet(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(session, user_id=user.id, action="entity_created", entity_type="timesheet", entity_id=obj.id, autocommit=True)
    return obj


@router.put("/timesheets/{ts_id}", response_model=TimesheetResponse)
async def update_timesheet(
    ts_id: int,
    payload: TimesheetUpdate,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    obj = await session.get(Timesheet, ts_id)
    if obj is None:
        raise not_found("timesheet", ts_id)
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    await session.commit()
    await session.refresh(obj)
    await audit_service.log(session, user_id=user.id, action="entity_updated", entity_type="timesheet", entity_id=ts_id, autocommit=True)
    return obj


# ── Day 4: brigade qualification queries ──────────────────────────────────────

class QualificationSummary(BaseModel):
    qualification_id: int
    qualification_name: str
    employee_count: int


@router.get("/brigades/{brigade_id}/qualifications", response_model=List[QualificationSummary], dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_brigade_qualifications(
    brigade_id: int, session: AsyncSession = Depends(get_db)
):
    """Return aggregated qualifications (unique) of all brigade members."""
    brigade = await session.get(Brigade, brigade_id)
    if brigade is None:
        raise not_found("brigade", brigade_id)

    from app.models.personnel import BrigadeMember, EmployeeQualification, Qualification
    from sqlalchemy import func

    rows = await session.execute(
        select(
            Qualification.id,
            Qualification.name,
            func.count(EmployeeQualification.employee_id).label("employee_count"),
        )
        .join(EmployeeQualification, EmployeeQualification.qualification_id == Qualification.id)
        .join(BrigadeMember, BrigadeMember.employee_id == EmployeeQualification.employee_id)
        .where(BrigadeMember.brigade_id == brigade_id)
        .group_by(Qualification.id, Qualification.name)
        .order_by(Qualification.name)
    )
    return [
        QualificationSummary(
            qualification_id=r[0],
            qualification_name=r[1],
            employee_count=r[2],
        )
        for r in rows.fetchall()
    ]


# ── Day 4: timesheet service endpoints ───────────────────────────────────────

class AutoFillRequest(BaseModel):
    employee_id: int
    year: int = Field(ge=2020, le=2035)
    month: int = Field(ge=1, le=12)


class AutoFillResponse(BaseModel):
    employee_id: int
    records_created: int


class MonthlySummaryResponse(BaseModel):
    employee_id: int
    year: int
    month: int
    regular_hours: Decimal
    overtime_hours: Decimal
    vacation_hours: Decimal
    sick_hours: Decimal
    total_hours: Decimal


class PayrollDataItemResponse(BaseModel):
    employee_id: int
    full_name: str
    position: str
    base_salary: Decimal
    regular_hours: Decimal
    overtime_hours: Decimal
    vacation_hours: Decimal
    sick_hours: Decimal
    total_estimated: Decimal


@router.post("/timesheets/auto-fill", response_model=AutoFillResponse)
async def auto_fill_timesheet(
    payload: AutoFillRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(HR_WRITE)),
):
    """Auto-fill regular working days (8h) for an employee in the given month."""
    import calendar
    from app.services.timesheet_service import auto_fill_timesheet as svc_fill

    first = date_type(payload.year, payload.month, 1)
    last = date_type(payload.year, payload.month, calendar.monthrange(payload.year, payload.month)[1])
    count = await svc_fill(session, employee_id=payload.employee_id, date_from=first, date_to=last)
    return AutoFillResponse(employee_id=payload.employee_id, records_created=count)


@router.get("/timesheets/summary", response_model=MonthlySummaryResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_timesheet_summary(
    employee_id: int = Query(...),
    year: int = Query(..., ge=2020, le=2035),
    month: int = Query(..., ge=1, le=12),
    session: AsyncSession = Depends(get_db),
):
    """Aggregate timesheet hours by type for a given employee and month."""
    from app.services.timesheet_service import get_monthly_summary

    summary = await get_monthly_summary(session, employee_id=employee_id, year=year, month=month)
    return MonthlySummaryResponse(
        employee_id=summary.employee_id,
        year=summary.year,
        month=summary.month,
        regular_hours=summary.regular_hours,
        overtime_hours=summary.overtime_hours,
        vacation_hours=summary.vacation_hours,
        sick_hours=summary.sick_hours,
        total_hours=summary.total_hours,
    )


@router.get("/timesheets/payroll-data", response_model=List[PayrollDataItemResponse], dependencies=[Depends(RoleChecker(HR_WRITE))])
async def get_payroll_data(
    year: int = Query(..., ge=2020, le=2035),
    month: int = Query(..., ge=1, le=12),
    session: AsyncSession = Depends(get_db),
):
    """Return payroll data for all active employees (for 1С export)."""
    from app.services.timesheet_service import get_payroll_data

    items = await get_payroll_data(session, year=year, month=month)
    return [
        PayrollDataItemResponse(
            employee_id=i.employee_id,
            full_name=i.full_name,
            position=i.position,
            base_salary=i.base_salary,
            regular_hours=i.regular_hours,
            overtime_hours=i.overtime_hours,
            vacation_hours=i.vacation_hours,
            sick_hours=i.sick_hours,
            total_estimated=i.total_estimated,
        )
        for i in items
    ]
