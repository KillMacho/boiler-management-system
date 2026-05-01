"""ML-подсистема: прогнозы нейросети."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.boilers import Boiler


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    boiler_id: Mapped[int] = mapped_column(ForeignKey("boilers.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.sysutcdatetime(), nullable=False
    )
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    predicted_failure_type: Mapped[Optional[str]] = mapped_column(String(100))
    horizon_minutes: Mapped[int] = mapped_column(nullable=False)
    triggered_alert: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0"
    )
    actual_outcome: Mapped[Optional[str]] = mapped_column(String(30))

    boiler: Mapped["Boiler"] = relationship(
        back_populates="ml_predictions", lazy="selectin"
    )
