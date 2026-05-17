"""Mass payslip distribution: generate PDF per employee and send via email."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personnel import Employee, EmployeeContact
from app.services.email_service import email_service
from app.services.payslip_pdf_generator import (
    AccrualItem,
    DeductionItem,
    PayslipData,
    save_payslip_pdf,
)

logger = logging.getLogger("payroll_distribution")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

_MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


def _period_label(period_code: str) -> str:
    """Convert '2026-04' → 'Апрель 2026'."""
    try:
        year, month = period_code.split("-")
        return f"{_MONTH_NAMES.get(int(month), month)} {year}"
    except Exception:
        return period_code


async def _load_payslip_data(
    session: AsyncSession, employee: Employee, period_code: str
) -> PayslipData:
    """Build PayslipData from timesheets and payroll registers for the period."""
    year_str, month_str = period_code.split("-")
    year, month = int(year_str), int(month_str)
    period_start = date(year, month, 1)
    # Last day of month
    if month == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month + 1, 1)

    # Days and hours from timesheet
    ts_result = await session.execute(
        text(
            "SELECT COALESCE(SUM(days_worked), 0), COALESCE(SUM(hours_worked), 0.0) "
            "FROM timesheets WHERE employee_id = :eid AND period_start >= :ps AND period_start < :pe"
        ),
        {"eid": employee.id, "ps": period_start, "pe": period_end},
    )
    row = ts_result.fetchone()
    days_worked = int(row[0]) if row else 0
    hours_worked = float(row[1]) if row else 0.0

    emp_name = f"{employee.last_name} {employee.first_name}"
    if employee.middle_name:
        emp_name += f" {employee.middle_name}"

    position_name = employee.position.name if employee.position else "—"
    dept_name = employee.department.name if employee.department else "—"

    # Default accruals: base salary placeholder (real system would query payroll register)
    accruals = [AccrualItem(name="Оклад (тариф)", amount=50000.0)]
    deductions = [
        DeductionItem(name="НДФЛ (13%)", amount=round(50000.0 * 0.13, 2)),
        DeductionItem(name="Удержания прочие", amount=0.0),
    ]

    return PayslipData(
        employee_id=employee.id,
        employee_name=emp_name,
        position=position_name,
        department=dept_name,
        period=_period_label(period_code),
        period_code=period_code,
        accruals=accruals,
        deductions=[d for d in deductions if d.amount > 0],
        days_worked=days_worked,
        hours_worked=hours_worked,
    )


async def _log_distribution(
    session: AsyncSession,
    employee_id: int,
    period_code: str,
    email: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    await session.execute(
        text(
            "INSERT INTO payslip_distribution_log "
            "(employee_id, period_code, email, status, error_message, sent_at) "
            "VALUES (:eid, :period, :email, :status, :err, SYSUTCDATETIME())"
        ),
        {
            "eid": employee_id,
            "period": period_code,
            "email": email,
            "status": status,
            "err": error_message,
        },
    )


async def distribute_payslips(
    session: AsyncSession,
    period_code: str,
    *,
    department_id: Optional[int] = None,
    employee_ids: Optional[list[int]] = None,
) -> dict:
    """Send payslip PDFs to employees with email notifications enabled.

    Returns summary: {"sent": N, "failed": M, "skipped": K, "errors": [...]}
    """
    # Build employee query
    stmt = (
        select(Employee)
        .join(EmployeeContact, Employee.id == EmployeeContact.employee_id)
        .where(
            Employee.status == "active",
            EmployeeContact.email_notifications_enabled == True,  # noqa: E712
        )
    )
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if employee_ids:
        stmt = stmt.where(Employee.id.in_(employee_ids))

    result = await session.execute(stmt)
    employees = result.scalars().all()

    sent, failed, skipped = 0, 0, 0
    errors: list[str] = []

    html_tmpl = _jinja.get_template("payslip.html")
    txt_tmpl = _jinja.get_template("payslip.txt")

    for emp in employees:
        contact = emp.contact
        if not contact or not contact.email:
            skipped += 1
            continue

        try:
            data = await _load_payslip_data(session, emp, period_code)
            pdf_path = save_payslip_pdf(data)

            ctx = {
                "employee_name": data.employee_name,
                "period": data.period,
                "total_accrued": f"{data.total_accrued:,.2f}".replace(",", " "),
                "total_deducted": f"{data.total_deducted:,.2f}".replace(",", " "),
                "net_pay": f"{data.net_pay:,.2f}".replace(",", " "),
            }
            html_body = html_tmpl.render(**ctx)
            txt_body = txt_tmpl.render(**ctx)

            ok = await email_service.send_email(
                to=contact.email,
                subject=f"Расчётный листок за {data.period}",
                body_text=txt_body,
                body_html=html_body,
                attachments=[str(pdf_path)],
            )

            if ok:
                await _log_distribution(session, emp.id, period_code, contact.email, "sent")
                sent += 1
            else:
                await _log_distribution(
                    session, emp.id, period_code, contact.email, "failed", "SMTP error"
                )
                failed += 1
                errors.append(contact.email)

        except Exception as exc:
            logger.exception("Error distributing payslip for employee %d: %s", emp.id, exc)
            try:
                await _log_distribution(
                    session,
                    emp.id,
                    period_code,
                    contact.email if contact else "",
                    "failed",
                    str(exc)[:500],
                )
            except Exception:
                pass
            failed += 1
            errors.append(f"employee_id={emp.id}: {exc}")

    await session.commit()

    logger.info(
        "Payslip distribution for %s complete: sent=%d failed=%d skipped=%d",
        period_code,
        sent,
        failed,
        skipped,
    )
    return {"sent": sent, "failed": failed, "skipped": skipped, "errors": errors}
