"""Integration endpoints: send period data to 1C and check 1C connectivity."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.services.onec_client import onec_client
from app.services.onec_period_service import send_period_to_onec
from app.services.permissions import ALL_ADMIN

router = APIRouter(prefix="/api/v1/integration", tags=["integration / 1C"])

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SendPeriodRequest(BaseModel):
    period: str = Field(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        examples=["2026-04"],
        description="Billing period in YYYY-MM format",
    )


class SendPeriodResponse(BaseModel):
    period: str
    acts_sent: int
    materials_sent: int
    transactions_sent: int
    timesheet_rows_sent: int
    acts_response: dict
    materials_response: dict
    transactions_response: dict
    timesheet_response: dict
    errors: list[str]
    success: bool


@router.post(
    "/onec/send-period",
    response_model=SendPeriodResponse,
    summary="Send all period data to 1C (acts, materials, transactions, timesheet)",
)
async def send_period(
    payload: SendPeriodRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> SendPeriodResponse:
    result = await send_period_to_onec(session, payload.period)
    return SendPeriodResponse(
        period=result.period,
        acts_sent=result.acts_sent,
        materials_sent=result.materials_sent,
        transactions_sent=result.transactions_sent,
        timesheet_rows_sent=result.timesheet_rows_sent,
        acts_response=result.acts_response,
        materials_response=result.materials_response,
        transactions_response=result.transactions_response,
        timesheet_response=result.timesheet_response,
        errors=result.errors,
        success=len(result.errors) == 0,
    )


@router.get(
    "/onec/health",
    summary="Check 1C mock server availability",
)
async def check_onec_health(_user=Depends(RoleChecker(ALL_ADMIN))) -> dict:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{onec_client._base_url}/health")
            if resp.status_code == 200:
                return {"статус": "ok", "onec_url": onec_client._base_url, "response": resp.json()}
            return {"статус": "error", "onec_url": onec_client._base_url, "http_status": resp.status_code}
    except Exception as exc:
        return {"статус": "unavailable", "onec_url": onec_client._base_url, "error": str(exc)}
