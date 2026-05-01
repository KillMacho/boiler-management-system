"""Телеметрия и пороги."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.boilers import Boiler


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    boiler_id: Mapped[int] = mapped_column(ForeignKey("boilers.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature_heat: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    pressure: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))
    co_level: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    gas_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    water_level: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    temperature_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    furnace_draft: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    boiler: Mapped["Boiler"] = relationship(
        back_populates="telemetry", lazy="selectin"
    )


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    boiler_id: Mapped[Optional[int]] = mapped_column(ForeignKey("boilers.id"))
    parameter_name: Mapped[str] = mapped_column(String(50), nullable=False)
    min_warning: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    max_warning: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    min_critical: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    max_critical: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))

    boiler: Mapped[Optional["Boiler"]] = relationship(
        back_populates="thresholds", lazy="selectin"
    )
