"""Reporting endpoints: generate XML reports, submit to EDO, track status."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.reporting import RegulatoryReport
from app.services import regulated_reporting
from app.services.edo_client import edo_client
from app.services.permissions import ALL_ADMIN

logger = logging.getLogger("reporting")
router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])

# Допустимые типы регуляторных отчётов
ReportTypeStr = Literal["6-NDFL", "RSV", "4-FSS", "SZV-STAZH"]

# Паттерны периодов: квартальные (2026-Q1) и годовые (2026 для СЗВ-СТАЖ)
_QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")
_YEAR_RE = re.compile(r"^\d{4}$")


# ── schemas ───────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    report_type: ReportTypeStr
    period: str = Field(..., examples=["2026-Q1", "2026"], description="YYYY-QN or YYYY for SZV-STAZH")


class GenerateResponse(BaseModel):
    id: int
    report_type: str
    period: str
    filepath: str
    size_bytes: int
    generated_at: str


class SubmitRequest(BaseModel):
    report_type: ReportTypeStr
    period: str
    inn: str = Field(default="7700000001")


class SubmitResponse(BaseModel):
    id: int
    report_type: str
    period: str
    submission_id: str
    receipt_number: str
    edo_status: str
    message: str


class ReportDetailResponse(BaseModel):
    id: int
    report_type: str
    period: str
    inn: str
    generated_at: str
    file_path: str
    file_size: int
    submission_id: Optional[str]
    receipt_number: Optional[str]
    edo_status: Optional[str]
    last_status_check: Optional[str]


# ── helpers ───────────────────────────────────────────────────────────────────

async def _generate(session: AsyncSession, report_type: str, period: str) -> regulated_reporting.ReportResult:
    if report_type == "6-NDFL":
        return await regulated_reporting.generate_6_ndfl(session, period)
    if report_type == "RSV":
        return await regulated_reporting.generate_rsv(session, period)
    if report_type == "4-FSS":
        return await regulated_reporting.generate_4_fss(session, period)
    if report_type == "SZV-STAZH":
        if not _YEAR_RE.match(period):
            raise HTTPException(422, detail="SZV-STAZH period must be YYYY (e.g. '2026')")
        return await regulated_reporting.generate_szv_stazh(session, int(period))
    raise HTTPException(422, detail=f"Unknown report_type '{report_type}'")


def _validate_period(report_type: str, period: str) -> None:
    if report_type == "SZV-STAZH":
        if not _YEAR_RE.match(period):
            raise HTTPException(422, detail="SZV-STAZH period must be YYYY")
    else:
        if not _QUARTER_RE.match(period):
            raise HTTPException(422, detail="Period must be YYYY-QN (e.g. '2026-Q1')")


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
async def generate_report(
    payload: GenerateRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> GenerateResponse:
    """Generate XML report and save metadata to DB."""
    _validate_period(payload.report_type, payload.period)
    result = await _generate(session, payload.report_type, payload.period)

    inn = getattr(settings, "edo_org_inn", "7700000001")
    report = RegulatoryReport(
        report_type=result.report_type,
        period=result.period,
        inn=inn,
        file_path=result.filepath,
        file_size=result.size_bytes,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    return GenerateResponse(
        id=report.id,
        report_type=report.report_type,
        period=report.period,
        filepath=report.file_path,
        size_bytes=report.file_size,
        generated_at=report.generated_at.isoformat(),
    )


@router.post("/submit", response_model=SubmitResponse)
async def submit_report(
    payload: SubmitRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> SubmitResponse:
    """Generate (if not yet) and submit XML report to EDO operator."""
    _validate_period(payload.report_type, payload.period)

    # Генерируем свежий XML и отправляем в ЭДО
    result = await _generate(session, payload.report_type, payload.period)

    # Submit to EDO
    try:
        edo_resp = await edo_client.submit_report(
            filepath=result.filepath,
            report_type=payload.report_type,
            period=payload.period,
            inn=payload.inn,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"EDO operator unavailable: {exc}",
        )

    sub_id = edo_resp.get("submission_id", "")
    receipt = edo_resp.get("receipt_number", "")

    report = RegulatoryReport(
        report_type=result.report_type,
        period=result.period,
        inn=payload.inn,
        file_path=result.filepath,
        file_size=result.size_bytes,
        submission_id=sub_id,
        receipt_number=receipt,
        edo_status="accepted",
        last_status_check=datetime.now(timezone.utc),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    return SubmitResponse(
        id=report.id,
        report_type=report.report_type,
        period=report.period,
        submission_id=sub_id,
        receipt_number=receipt,
        edo_status="accepted",
        message=edo_resp.get("message", "Отчёт принят"),
    )


@router.get("/list", response_model=list[ReportDetailResponse])
async def list_reports(
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> list[ReportDetailResponse]:
    rows = await session.execute(
        select(RegulatoryReport).order_by(RegulatoryReport.generated_at.desc())
    )
    reports = list(rows.scalars().all())
    return [_to_detail(r) for r in reports]


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> ReportDetailResponse:
    report = await session.get(RegulatoryReport, report_id)
    if not report:
        raise HTTPException(404, detail="Report not found")

    # Refresh EDO status if submitted
    # Если отчёт уже отправлен — обновляем статус из ЭДО (ошибка не критична)
    if report.submission_id:
        try:
            status_resp = await edo_client.check_status(report.submission_id)
            report.edo_status = status_resp.get("status")
            report.last_status_check = datetime.now(timezone.utc)
            await session.commit()
        except Exception:
            pass  # status check failure is non-fatal

    return _to_detail(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _user=Depends(RoleChecker(ALL_ADMIN)),
) -> FileResponse:
    report = await session.get(RegulatoryReport, report_id)
    if not report:
        raise HTTPException(404, detail="Report not found")
    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(404, detail="Report file not found on disk")
    return FileResponse(
        path=str(path),
        media_type="application/xml",
        filename=path.name,
    )


def _to_detail(r: RegulatoryReport) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=r.id,
        report_type=r.report_type,
        period=r.period,
        inn=r.inn,
        generated_at=r.generated_at.isoformat(),
        file_path=r.file_path,
        file_size=r.file_size,
        submission_id=r.submission_id,
        receipt_number=r.receipt_number,
        edo_status=r.edo_status,
        last_status_check=r.last_status_check.isoformat() if r.last_status_check else None,
    )
