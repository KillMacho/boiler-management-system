"""POST /api/v1/submission/upload and GET /api/v1/submission/list."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, status
from fastapi.responses import JSONResponse

from app.auth import require_api_key
from app.schemas import ReportType, SubmissionMeta, UploadResponse
from app.storage import storage

logger = logging.getLogger("edo_mock.submission")
router = APIRouter(prefix="/api/v1/submission", tags=["submission"])


@router.post("/upload", response_model=UploadResponse)
async def upload_report(
    file: UploadFile,
    report_type: ReportType = Form(...),
    period: str = Form(...),
    inn: str = Form(...),
    _key: str = Depends(require_api_key),
) -> UploadResponse:
    content = await file.read()
    filename = file.filename or f"{report_type}_{period}.xml"

    record, receipt = storage.save_submission(
        report_type=report_type,
        period=period,
        inn=inn,
        filename=filename,
        file_content=content,
    )
    logger.info(
        "report uploaded: type=%s period=%s inn=%s size=%d sub_id=%s",
        report_type, period, inn, len(content), record.submission_id,
    )
    return UploadResponse(
        submission_id=record.submission_id,
        receipt_number=receipt,
        status="accepted",
        received_at=record.received_at,
        estimated_processing_minutes=15,
        message="Отчёт принят к обработке оператором",
    )


@router.get("/list", response_model=list[SubmissionMeta])
async def list_submissions(
    inn: str,
    period: str,
    _key: str = Depends(require_api_key),
) -> list[SubmissionMeta]:
    records = storage.list_by_inn_period(inn, period)
    return [
        SubmissionMeta(
            submission_id=r.submission_id,
            report_type=r.report_type,
            period=r.period,
            inn=r.inn,
            filename=r.filename,
            received_at=r.received_at,
            status=r.status,
            file_size_bytes=r.file_size_bytes,
        )
        for r in records
    ]
