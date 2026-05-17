"""Notifications router — email-related endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.services.email_service import email_service
from app.services.notifications_service import (
    notify_alarm,
    notify_brigade_assigned,
    notify_new_request,
    notify_report_ready,
    notify_work_order_completed,
)
from app.services.payroll_distribution_service import distribute_payslips
from app.services.permissions import ALL_ADMIN

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# Рассылку расчётных листков разрешаем не только администраторам, но и финансовому персоналу
_FINANCE_ROLES = ALL_ADMIN + ["accountant", "hr_officer"]


# ── Schemas ───────────────────────────────────────────────────────────────────

class SendTestEmailRequest(BaseModel):
    to: EmailStr
    subject: str = "Тестовое письмо"
    body: str = "Это тестовое письмо от системы Котельный сервис."


class DistributePayslipsRequest(BaseModel):
    period_code: str  # YYYY-MM
    department_id: Optional[int] = None
    employee_ids: Optional[list[int]] = None

    # Валидация формата периода — защита от некорректных данных на уровне схемы
    @field_validator("period_code")
    @classmethod
    def validate_period(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("period_code must be in YYYY-MM format")
        return v


class NotifyRequestRequest(BaseModel):
    request_number: str
    boiler_name: str
    request_type: str
    priority: str
    description: str
    created_at: str


class NotifyAlarmRequest(BaseModel):
    boiler_name: str
    parameter_name: str
    value: str
    threshold_kind: str
    detected_at: str
    request_number: str


class NotifyReportRequest(BaseModel):
    to_emails: list[EmailStr]
    report_type: str
    period: str
    generated_at: str
    file_size: str
    file_path: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/test-email",
    summary="Отправить тестовое письмо",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker(ALL_ADMIN))],
)
async def send_test_email(body: SendTestEmailRequest) -> dict:
    ok = await email_service.send_email(
        to=body.to,
        subject=body.subject,
        body_text=body.body,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to send email via SMTP")
    return {"status": "sent", "to": body.to}


@router.post(
    "/payslips/distribute",
    summary="Массовая рассылка расчётных листков",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker(_FINANCE_ROLES))],
)
async def distribute(
    body: DistributePayslipsRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await distribute_payslips(
        session,
        body.period_code,
        department_id=body.department_id,
        employee_ids=body.employee_ids,
    )
    return result


@router.post(
    "/events/new-request",
    summary="Уведомление о новой заявке (вызывается внутренне)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker(ALL_ADMIN))],
)
async def event_new_request(
    body: NotifyRequestRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await notify_new_request(
        session,
        request_number=body.request_number,
        boiler_name=body.boiler_name,
        request_type=body.request_type,
        priority=body.priority,
        description=body.description,
        created_at=body.created_at,
    )
    return {"status": "dispatched"}


@router.post(
    "/events/alarm",
    summary="Уведомление об аварийной ситуации",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker(ALL_ADMIN))],
)
async def event_alarm(
    body: NotifyAlarmRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await notify_alarm(
        session,
        boiler_name=body.boiler_name,
        parameter_name=body.parameter_name,
        value=body.value,
        threshold_kind=body.threshold_kind,
        detected_at=body.detected_at,
        request_number=body.request_number,
    )
    return {"status": "dispatched"}


@router.post(
    "/events/report-ready",
    summary="Уведомление о готовом отчёте с вложением",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker(_FINANCE_ROLES))],
)
async def event_report_ready(
    body: NotifyReportRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await notify_report_ready(
        session,
        to_emails=list(body.to_emails),
        report_type=body.report_type,
        period=body.period,
        generated_at=body.generated_at,
        file_size=body.file_size,
        file_path=body.file_path,
    )
    return {"status": "dispatched"}
