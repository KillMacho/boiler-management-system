"""Admin endpoints — no auth — for demo inspection during defence."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.schemas import SubmissionMeta
from app.storage import storage

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/all", response_model=list[SubmissionMeta])
async def get_all() -> list[SubmissionMeta]:
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
        for r in storage.list_all()
    ]


@router.get("/file/{submission_id}", summary="Download the submitted XML file")
async def download_file(submission_id: str) -> FileResponse:
    file_path = storage.get_file_path(submission_id)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    return FileResponse(
        path=str(path),
        media_type="application/xml",
        filename=path.name,
    )


@router.delete("/clear", summary="Clear all stored submissions (for repeated tests)")
async def clear_all() -> dict:
    storage.clear()
    return {"status": "ok", "message": "Все отправки очищены"}
