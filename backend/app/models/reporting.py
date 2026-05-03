"""ORM model for regulatory XML reports and their EDO submission status."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RegulatoryReport(Base):
    __tablename__ = "regulatory_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    submission_id: Mapped[Optional[str]] = mapped_column(String(50))
    receipt_number: Mapped[Optional[str]] = mapped_column(String(100))
    edo_status: Mapped[Optional[str]] = mapped_column(String(50))
    last_status_check: Mapped[Optional[datetime]] = mapped_column(DateTime)
