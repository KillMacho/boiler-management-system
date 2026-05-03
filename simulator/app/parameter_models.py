"""Normal operating ranges and standard deviations for each telemetry parameter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParameterSpec:
    normal_mean: float    # typical operating value
    normal_std: float     # Gaussian noise σ
    unit: str             # display unit for logging


# Keyed by the field name sent to POST /api/v1/telemetry/
PARAMETER_SPECS: dict[str, ParameterSpec] = {
    "temperature_heat": ParameterSpec(
        normal_mean=75.0,
        normal_std=3.0,
        unit="°C",
    ),
    "pressure": ParameterSpec(
        normal_mean=0.40,
        normal_std=0.02,
        unit="MPa",
    ),
    "co_level": ParameterSpec(
        normal_mean=12.0,
        normal_std=2.0,
        unit="mg/m³",
    ),
    "gas_flow": ParameterSpec(
        normal_mean=55.0,
        normal_std=4.0,
        unit="m³/h",
    ),
    "water_level": ParameterSpec(
        normal_mean=260.0,
        normal_std=10.0,
        unit="mm",
    ),
    "temperature_return": ParameterSpec(
        normal_mean=55.0,
        normal_std=2.5,
        unit="°C",
    ),
    "furnace_draft": ParameterSpec(
        normal_mean=-20.0,
        normal_std=2.0,
        unit="Pa",
    ),
}

# Threshold reference values (mirror of DB defaults) — used only for scenario generation
CRITICAL_HIGH: dict[str, float] = {
    "temperature_heat": 105.0,
    "pressure": 0.60,
    "co_level": 50.0,
    "gas_flow": 90.0,
    "water_level": 350.0,
    "temperature_return": 80.0,
    "furnace_draft": -5.0,
}

CRITICAL_LOW: dict[str, float] = {
    "temperature_heat": 40.0,
    "pressure": 0.10,
    "co_level": 0.0,
    "gas_flow": 10.0,
    "water_level": 150.0,
    "temperature_return": 30.0,
    "furnace_draft": -45.0,
}
