"""BoilerSimulator: generates realistic telemetry readings with optional alarm injection."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .parameter_models import PARAMETER_SPECS

logger = logging.getLogger("simulator.boiler")


@dataclass
class TelemetryReading:
    boiler_id: int
    timestamp: str  # ISO-8601 UTC
    temperature_heat: float
    pressure: float
    co_level: float
    gas_flow: float
    water_level: float
    temperature_return: float
    furnace_draft: float

    def to_dict(self) -> dict:
        return {
            "boiler_id": self.boiler_id,
            "timestamp": self.timestamp,
            "temperature_heat": round(self.temperature_heat, 2),
            "pressure": round(self.pressure, 4),
            "co_level": round(self.co_level, 2),
            "gas_flow": round(self.gas_flow, 2),
            "water_level": round(self.water_level, 1),
            "temperature_return": round(self.temperature_return, 2),
            "furnace_draft": round(self.furnace_draft, 2),
        }


class BoilerSimulator:
    """Simulates a single boiler.

    In normal mode each parameter is sampled from a Gaussian around its mean.
    In alarm mode the current scenario overrides specific parameters until reset.
    """

    def __init__(self, boiler_id: int) -> None:
        self.boiler_id = boiler_id
        self._alarm_overrides: dict[str, float] = {}
        self._alarm_name: Optional[str] = None
        # Slight per-boiler offset so all 15 boilers don't read identically
        self._offset: dict[str, float] = {
            name: random.gauss(0, spec.normal_std * 0.3)
            for name, spec in PARAMETER_SPECS.items()
        }

    @property
    def is_in_alarm(self) -> bool:
        return bool(self._alarm_overrides)

    @property
    def alarm_name(self) -> Optional[str]:
        return self._alarm_name

    def trigger_alarm(self, name: str, overrides: dict[str, float]) -> None:
        self._alarm_name = name
        self._alarm_overrides = overrides
        logger.warning("boiler_id=%d alarm triggered: %s", self.boiler_id, name)

    def reset_to_normal(self) -> None:
        if self._alarm_name:
            logger.info("boiler_id=%d alarm cleared: %s", self.boiler_id, self._alarm_name)
        self._alarm_name = None
        self._alarm_overrides = {}

    def generate_reading(self) -> TelemetryReading:
        values: dict[str, float] = {}
        for name, spec in PARAMETER_SPECS.items():
            if name in self._alarm_overrides:
                # Alarm value with small noise so it looks realistic in logs
                base = self._alarm_overrides[name]
                values[name] = base + random.gauss(0, spec.normal_std * 0.1)
            else:
                values[name] = (
                    spec.normal_mean
                    + self._offset[name]
                    + random.gauss(0, spec.normal_std)
                )

        return TelemetryReading(
            boiler_id=self.boiler_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **values,  # type: ignore[arg-type]
        )
