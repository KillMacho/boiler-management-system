"""Timesheet management: auto-fill, monthly summary, payroll data for 1С."""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personnel import Employee, Position, Timesheet

logger = logging.getLogger("timesheet_service")

_WORK_HOURS_PER_DAY = Decimal("8")
_STANDARD_HOURS_PER_MONTH = Decimal("176")
_OVERTIME_COEFFICIENT = Decimal("1.5")


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday = 5, Sunday = 6


def _iter_working_days(date_from: date, date_to: date):
    d = date_from
    while d <= date_to:
        if not _is_weekend(d):
            yield d
        d += timedelta(days=1)


async def auto_fill_timesheet(
    session: AsyncSession,
    *,
    employee_id: int,
    date_from: date,
    date_to: date,
    hours_type: str = "regular",
) -> int:
    """Fill timesheet with regular working days (8 h) for a given range.

    Skips weekends and days that already have a record.
    Returns number of records created.
    """
    # Load existing records for the range to avoid duplicates
    existing_rows = await session.execute(
        select(Timesheet.date).where(
            Timesheet.employee_id == employee_id,
            Timesheet.date >= date_from,
            Timesheet.date <= date_to,
        )
    )
    existing_dates: set[date] = {r[0] for r in existing_rows.fetchall()}

    count = 0
    for d in _iter_working_days(date_from, date_to):
        if d not in existing_dates:
            session.add(
                Timesheet(
                    employee_id=employee_id,
                    date=d,
                    hours_worked=_WORK_HOURS_PER_DAY,
                    hours_type=hours_type,
                )
            )
            count += 1

    if count > 0:
        await session.commit()
    logger.info("auto_fill: employee_id=%s created=%s records", employee_id, count)
    return count


@dataclass
class MonthlySummary:
    employee_id: int
    year: int
    month: int
    regular_hours: Decimal
    overtime_hours: Decimal
    vacation_hours: Decimal
    sick_hours: Decimal

    @property
    def total_hours(self) -> Decimal:
        return self.regular_hours + self.overtime_hours + self.vacation_hours + self.sick_hours


async def get_monthly_summary(
    session: AsyncSession,
    *,
    employee_id: int,
    year: int,
    month: int,
) -> MonthlySummary:
    """Aggregate timesheet hours by type for a given month."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])

    rows = await session.execute(
        select(Timesheet).where(
            Timesheet.employee_id == employee_id,
            Timesheet.date >= first,
            Timesheet.date <= last,
        )
    )
    timesheets = list(rows.scalars().all())

    summary = MonthlySummary(
        employee_id=employee_id,
        year=year,
        month=month,
        regular_hours=Decimal("0"),
        overtime_hours=Decimal("0"),
        vacation_hours=Decimal("0"),
        sick_hours=Decimal("0"),
    )
    for ts in timesheets:
        if ts.hours_type == "regular":
            summary.regular_hours += ts.hours_worked
        elif ts.hours_type == "overtime":
            summary.overtime_hours += ts.hours_worked
        elif ts.hours_type == "vacation":
            summary.vacation_hours += ts.hours_worked
        elif ts.hours_type == "sick":
            summary.sick_hours += ts.hours_worked

    return summary


@dataclass
class PayrollDataItem:
    employee_id: int
    full_name: str
    position: str
    base_salary: Decimal
    regular_hours: Decimal
    overtime_hours: Decimal
    vacation_hours: Decimal
    sick_hours: Decimal
    total_estimated: Decimal


async def get_payroll_data(
    session: AsyncSession,
    *,
    year: int,
    month: int,
) -> list[PayrollDataItem]:
    """Build payroll data for all active employees for a given month.

    Estimated amount:
      regular_pay  = base_salary  (if regular_hours >= 160, else base_salary * hours / 176)
      overtime_pay = (base_salary / 176) * 1.5 * overtime_hours
      total        = regular_pay + overtime_pay
    """
    emp_rows = await session.execute(
        select(Employee)
        .where(Employee.status == "active")
    )
    employees = list(emp_rows.scalars().all())

    result: list[PayrollDataItem] = []
    for emp in employees:
        position: Optional[Position] = await session.get(Position, emp.position_id)
        base_salary = position.base_salary if position else Decimal("0")

        summary = await get_monthly_summary(
            session, employee_id=emp.id, year=year, month=month
        )

        hourly_rate = base_salary / _STANDARD_HOURS_PER_MONTH if base_salary else Decimal("0")
        if summary.regular_hours >= Decimal("160"):
            regular_pay = base_salary
        else:
            regular_pay = hourly_rate * summary.regular_hours

        overtime_pay = hourly_rate * _OVERTIME_COEFFICIENT * summary.overtime_hours
        total_estimated = regular_pay + overtime_pay

        result.append(
            PayrollDataItem(
                employee_id=emp.id,
                full_name=f"{emp.last_name} {emp.first_name} {emp.middle_name or ''}".strip(),
                position=position.name if position else "",
                base_salary=base_salary,
                regular_hours=summary.regular_hours,
                overtime_hours=summary.overtime_hours,
                vacation_hours=summary.vacation_hours,
                sick_hours=summary.sick_hours,
                total_estimated=total_estimated.quantize(Decimal("0.01")),
            )
        )

    return result
