"""Business-event notification dispatcher.

Each public function corresponds to one event type.
It renders the Jinja2 template, then calls email_service.send_email.
All recipients come from the DB (by role or explicit list) — no hardcoded emails.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personnel import Employee, EmployeeContact
from app.models.users import User
from app.services.email_service import email_service

logger = logging.getLogger("notifications_service")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, **ctx) -> tuple[str, str]:
    """Return (html_body, txt_body)."""
    html = _jinja.get_template(f"{template_name}.html").render(**ctx)
    txt = _jinja.get_template(f"{template_name}.txt").render(**ctx)
    return html, txt


async def _emails_for_roles(session: AsyncSession, roles: list[str]) -> list[str]:
    """Collect unique email addresses for users with any of the given roles."""
    result = await session.execute(
        text(
            "SELECT DISTINCT ec.email "
            "FROM employee_contacts ec "
            "JOIN employees e ON ec.employee_id = e.id "
            "JOIN users u ON u.employee_id = e.id "
            "JOIN user_roles ur ON ur.user_id = u.id "
            "JOIN roles r ON r.id = ur.role_id "
            "WHERE r.name IN :roles "
            "  AND e.status = 'active' "
            "  AND ec.email_notifications_enabled = 1"
        ),
        {"roles": tuple(roles)},
    )
    return [row[0] for row in result.fetchall()]


async def notify_new_request(
    session: AsyncSession,
    *,
    request_number: str,
    boiler_name: str,
    request_type: str,
    priority: str,
    description: str,
    created_at: str,
) -> None:
    """Notify dispatchers and chief engineers about a new service request."""
    recipients = await _emails_for_roles(session, ["dispatcher", "chief_engineer"])
    if not recipients:
        logger.info("notify_new_request: no recipients found, skipping")
        return

    html, txt = _render(
        "new_request",
        request_number=request_number,
        boiler_name=boiler_name,
        request_type=request_type,
        priority=priority,
        description=description,
        created_at=created_at,
    )
    result = await email_service.send_bulk(
        recipients=recipients,
        subject=f"Новая заявка {request_number} — {boiler_name}",
        body_text=txt,
        body_html=html,
    )
    logger.info("notify_new_request: %s", result)


async def notify_brigade_assigned(
    session: AsyncSession,
    *,
    brigade_leader_employee_id: int,
    request_number: str,
    boiler_name: str,
    work_order_number: str,
    brigade_name: str,
    scheduled_date: str,
) -> None:
    """Notify brigade leader about assignment."""
    result = await session.execute(
        select(EmployeeContact).where(
            EmployeeContact.employee_id == brigade_leader_employee_id,
            EmployeeContact.email_notifications_enabled == True,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        logger.info("notify_brigade_assigned: leader %d has no email", brigade_leader_employee_id)
        return

    emp_result = await session.execute(
        select(Employee).where(Employee.id == brigade_leader_employee_id)
    )
    emp = emp_result.scalar_one_or_none()
    employee_name = (
        f"{emp.last_name} {emp.first_name}" if emp else "Бригадир"
    )

    html, txt = _render(
        "brigade_assigned",
        employee_name=employee_name,
        request_number=request_number,
        boiler_name=boiler_name,
        work_order_number=work_order_number,
        brigade_name=brigade_name,
        scheduled_date=scheduled_date,
    )
    ok = await email_service.send_email(
        to=contact.email,
        subject=f"Наряд {work_order_number} назначен Вашей бригаде",
        body_text=txt,
        body_html=html,
    )
    logger.info("notify_brigade_assigned: employee=%d ok=%s", brigade_leader_employee_id, ok)


async def notify_alarm(
    session: AsyncSession,
    *,
    boiler_name: str,
    parameter_name: str,
    value: str,
    threshold_kind: str,
    detected_at: str,
    request_number: str,
) -> None:
    """Notify dispatchers and chief engineers about a critical alarm."""
    recipients = await _emails_for_roles(session, ["dispatcher", "chief_engineer"])
    if not recipients:
        logger.info("notify_alarm: no recipients, skipping")
        return

    html, txt = _render(
        "alarm_alert",
        boiler_name=boiler_name,
        parameter_name=parameter_name,
        value=value,
        threshold_kind=threshold_kind,
        detected_at=detected_at,
        request_number=request_number,
    )
    result = await email_service.send_bulk(
        recipients=recipients,
        subject=f"АВАРИЯ: {boiler_name} — {parameter_name}={value}",
        body_text=txt,
        body_html=html,
    )
    logger.info("notify_alarm: %s", result)


async def notify_work_order_completed(
    session: AsyncSession,
    *,
    work_order_number: str,
    request_number: str,
    boiler_name: str,
    brigade_name: str,
    completed_at: str,
    notes: Optional[str] = None,
) -> None:
    """Notify dispatchers when a work order is completed."""
    recipients = await _emails_for_roles(session, ["dispatcher", "chief_engineer"])
    if not recipients:
        return

    html, txt = _render(
        "work_order_completed",
        work_order_number=work_order_number,
        request_number=request_number,
        boiler_name=boiler_name,
        brigade_name=brigade_name,
        completed_at=completed_at,
        notes=notes or "",
    )
    result = await email_service.send_bulk(
        recipients=recipients,
        subject=f"Наряд {work_order_number} выполнен — {boiler_name}",
        body_text=txt,
        body_html=html,
    )
    logger.info("notify_work_order_completed: %s", result)


async def notify_report_ready(
    session: AsyncSession,
    *,
    to_emails: list[str],
    report_type: str,
    period: str,
    generated_at: str,
    file_size: str,
    file_path: Optional[str] = None,
) -> None:
    """Notify accountants/admins that a regulatory report is ready."""
    html, txt = _render(
        "report_ready",
        report_type=report_type,
        period=period,
        generated_at=generated_at,
        file_size=file_size,
    )
    attachments = [file_path] if file_path else None
    result = await email_service.send_bulk(
        recipients=to_emails,
        subject=f"Отчёт {report_type} за {period} сформирован",
        body_text=txt,
        body_html=html,
        attachments=attachments,
    )
    logger.info("notify_report_ready: %s", result)
