"""GET /api/v1/status/{submission_id} — document flow status with time-based progression."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_api_key
from app.schemas import AuthorityConfirmation, StatusResponse
from app.storage import storage

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/{submission_id}", response_model=StatusResponse)
async def get_status(
    submission_id: str,
    _key: str = Depends(require_api_key),
) -> StatusResponse:
    record = storage.get_status(submission_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' не найден",
        )

    confirmation = None
    if record.status == "confirmed":
        from datetime import datetime, timezone
        confirmation = AuthorityConfirmation(
            confirmation_number=f"ФНС-{record.received_at[:10].replace('-', '')}-{record.submission_id[-5:]}",
            received_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    return StatusResponse(
        submission_id=record.submission_id,
        status=record.status,
        history=record.history,
        authority_confirmation=confirmation,
    )
