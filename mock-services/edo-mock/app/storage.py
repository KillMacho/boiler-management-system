"""In-memory + disk storage for EDO submissions.

Each submission gets:
  - metadata dict in memory (fast lookup)
  - XML file on disk at storage_dir/{submission_id}/{filename}.xml
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import settings
from .schemas import EdoStatus, ReportType, StatusHistoryItem


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SubmissionRecord:
    submission_id: str
    report_type: ReportType
    period: str
    inn: str
    filename: str
    received_at: str
    file_path: str          # absolute path on disk
    file_size_bytes: int
    status: EdoStatus = "accepted"
    history: list[StatusHistoryItem] = field(default_factory=list)
    first_status_check_at: Optional[float] = None  # epoch seconds


class EDOMockStorage:
    def __init__(self) -> None:
        self._submissions: dict[str, SubmissionRecord] = {}
        self._counter: int = 0

    # ── submission IDs ────────────────────────────────────────────────────────

    def _next_submission_id(self) -> str:
        self._counter += 1
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"SUB-{today}-{self._counter:05d}"

    def _receipt_number(self, submission_id: str) -> str:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"КВТ-7700-{today}-{self._counter:05d}"

    # ── save submission ───────────────────────────────────────────────────────

    def save_submission(
        self,
        report_type: ReportType,
        period: str,
        inn: str,
        filename: str,
        file_content: bytes,
    ) -> tuple[SubmissionRecord, str]:
        """Persist file to disk, create metadata record. Returns (record, receipt_number)."""
        sub_id = self._next_submission_id()
        receipt = self._receipt_number(sub_id)
        now = _now_iso()

        # Write to disk
        sub_dir = Path(settings.storage_dir) / sub_id
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / filename
        file_path.write_bytes(file_content)

        record = SubmissionRecord(
            submission_id=sub_id,
            report_type=report_type,
            period=period,
            inn=inn,
            filename=filename,
            received_at=now,
            file_path=str(file_path),
            file_size_bytes=len(file_content),
            status="accepted",
            history=[
                StatusHistoryItem(
                    timestamp=now,
                    status="accepted",
                    message="Принято оператором ЭДО",
                )
            ],
        )
        self._submissions[sub_id] = record
        return record, receipt

    # ── status with time-based progression ───────────────────────────────────

    def get_status(self, submission_id: str) -> Optional[SubmissionRecord]:
        record = self._submissions.get(submission_id)
        if record is None:
            return None

        import time

        now = time.monotonic()

        # Record first check time
        if record.first_status_check_at is None:
            record.first_status_check_at = now

        elapsed = now - record.first_status_check_at
        new_status: EdoStatus

        if elapsed >= 15:
            new_status = "confirmed"
        elif elapsed >= 10:
            new_status = "delivered_to_authority"
        elif elapsed >= 5:
            new_status = "processing"
        else:
            new_status = "accepted"

        if new_status != record.status:
            record.status = new_status
            messages: dict[EdoStatus, str] = {
                "processing": "Передано в ФНС на обработку",
                "delivered_to_authority": "Получено контролирующим органом",
                "confirmed": "Подтверждено контролирующим органом",
            }
            record.history.append(
                StatusHistoryItem(
                    timestamp=_now_iso(),
                    status=new_status,
                    message=messages.get(new_status, new_status),
                )
            )

        return record

    # ── queries ───────────────────────────────────────────────────────────────

    def list_all(self) -> list[SubmissionRecord]:
        return list(self._submissions.values())

    def list_by_inn_period(self, inn: str, period: str) -> list[SubmissionRecord]:
        return [
            r for r in self._submissions.values()
            if r.inn == inn and r.period == period
        ]

    def get_file_path(self, submission_id: str) -> Optional[str]:
        rec = self._submissions.get(submission_id)
        return rec.file_path if rec else None

    def clear(self) -> None:
        self._submissions.clear()
        self._counter = 0


storage = EDOMockStorage()
