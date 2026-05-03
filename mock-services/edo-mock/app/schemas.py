"""Pydantic schemas for EDO mock API."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel

ReportType = Literal["6-NDFL", "RSV", "4-FSS", "SZV-STAZH"]

EdoStatus = Literal[
    "accepted",
    "processing",
    "delivered_to_authority",
    "confirmed",
    "rejected",
]


class UploadResponse(BaseModel):
    submission_id: str
    receipt_number: str
    status: EdoStatus
    received_at: str
    estimated_processing_minutes: int
    message: str


class StatusHistoryItem(BaseModel):
    timestamp: str
    status: EdoStatus
    message: str


class AuthorityConfirmation(BaseModel):
    confirmation_number: str
    received_at: str


class StatusResponse(BaseModel):
    submission_id: str
    status: EdoStatus
    history: list[StatusHistoryItem]
    authority_confirmation: Optional[AuthorityConfirmation] = None


class SubmissionMeta(BaseModel):
    submission_id: str
    report_type: ReportType
    period: str
    inn: str
    filename: str
    received_at: str
    status: EdoStatus
    file_size_bytes: int
