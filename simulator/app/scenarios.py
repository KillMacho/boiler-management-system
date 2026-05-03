"""Alarm scenario definitions: each scenario returns a parameter override dict."""
from __future__ import annotations

import random
from typing import Callable

# Each scenario function returns a dict[param_name, value] that overrides normal generation.
# Values are chosen to cross critical thresholds reliably.

ScenarioFn = Callable[[], dict[str, float]]


def _overheat() -> dict[str, float]:
    """Supply temperature climbs above 105°C critical threshold."""
    return {
        "temperature_heat": random.uniform(110.0, 130.0),
        "temperature_return": random.uniform(82.0, 92.0),
        "pressure": random.uniform(0.45, 0.55),
    }


def _leak() -> dict[str, float]:
    """Pressure drops sharply below 0.10 MPa — possible pipe leak."""
    return {
        "pressure": random.uniform(0.05, 0.09),
        "water_level": random.uniform(140.0, 160.0),
        "gas_flow": random.uniform(35.0, 45.0),
    }


def _co_spike() -> dict[str, float]:
    """CO level spikes above 50 mg/m³ — incomplete combustion or sensor fault."""
    return {
        "co_level": random.uniform(55.0, 90.0),
        "furnace_draft": random.uniform(-8.0, -3.0),
    }


def _draft_failure() -> dict[str, float]:
    """Furnace draft collapses (near zero) — chimney blockage."""
    return {
        "furnace_draft": random.uniform(-2.0, 1.0),
        "co_level": random.uniform(40.0, 65.0),
    }


def _low_water() -> dict[str, float]:
    """Water level in drum drops below 150 mm — protection trip risk."""
    return {
        "water_level": random.uniform(100.0, 145.0),
        "temperature_heat": random.uniform(100.0, 115.0),
    }


# Registered scenarios — main loop picks uniformly at random
SCENARIOS: list[tuple[str, ScenarioFn]] = [
    ("overheat", _overheat),
    ("leak", _leak),
    ("co_spike", _co_spike),
    ("draft_failure", _draft_failure),
    ("low_water", _low_water),
]


def random_scenario() -> tuple[str, dict[str, float]]:
    """Return (name, overrides) for a randomly chosen alarm scenario."""
    name, fn = random.choice(SCENARIOS)
    return name, fn()


def get_scenario(name: str) -> dict[str, float]:
    """Return overrides for a named scenario; raises KeyError if unknown."""
    mapping = {n: fn for n, fn in SCENARIOS}
    if name not in mapping:
        raise KeyError(f"Unknown scenario '{name}'. Available: {list(mapping)}")
    return mapping[name]()
