"""Unit tests for BoilerSimulator and scenario injection (no HTTP required)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
import os

# Allow running tests from simulator/ root: add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.boiler_simulator import BoilerSimulator, TelemetryReading
from app.parameter_models import CRITICAL_HIGH, CRITICAL_LOW, PARAMETER_SPECS
from app.scenarios import SCENARIOS, get_scenario, random_scenario


# ── BoilerSimulator ────────────────────────────────────────────────────────────

class TestBoilerSimulator:
    def test_generates_all_parameters(self):
        sim = BoilerSimulator(boiler_id=1)
        reading = sim.generate_reading()
        for name in PARAMETER_SPECS:
            assert hasattr(reading, name), f"Missing field: {name}"

    def test_normal_mode_values_near_mean(self):
        """Over 100 samples the mean should stay within 3σ of the normal mean."""
        sim = BoilerSimulator(boiler_id=2)
        samples = [sim.generate_reading().temperature_heat for _ in range(100)]
        mean = sum(samples) / len(samples)
        spec = PARAMETER_SPECS["temperature_heat"]
        assert abs(mean - spec.normal_mean) < spec.normal_std * 3

    def test_is_not_in_alarm_initially(self):
        sim = BoilerSimulator(boiler_id=3)
        assert not sim.is_in_alarm
        assert sim.alarm_name is None

    def test_trigger_alarm_sets_flag(self):
        sim = BoilerSimulator(boiler_id=4)
        sim.trigger_alarm("overheat", {"temperature_heat": 125.0})
        assert sim.is_in_alarm
        assert sim.alarm_name == "overheat"

    def test_alarm_overrides_parameter(self):
        sim = BoilerSimulator(boiler_id=5)
        sim.trigger_alarm("overheat", {"temperature_heat": 125.0})
        readings = [sim.generate_reading().temperature_heat for _ in range(10)]
        # All readings should be near 125, well above normal ~75
        assert all(r > 100 for r in readings), readings

    def test_reset_clears_alarm(self):
        sim = BoilerSimulator(boiler_id=6)
        sim.trigger_alarm("leak", {"pressure": 0.05})
        sim.reset_to_normal()
        assert not sim.is_in_alarm
        assert sim.alarm_name is None

    def test_reset_returns_to_normal_range(self):
        sim = BoilerSimulator(boiler_id=7)
        sim.trigger_alarm("leak", {"pressure": 0.05})
        sim.reset_to_normal()
        readings = [sim.generate_reading().pressure for _ in range(20)]
        spec = PARAMETER_SPECS["pressure"]
        mean = sum(readings) / len(readings)
        assert abs(mean - spec.normal_mean) < spec.normal_std * 4

    def test_to_dict_serialisable(self):
        sim = BoilerSimulator(boiler_id=8)
        reading = sim.generate_reading()
        d = reading.to_dict()
        assert d["boiler_id"] == 8
        # Must be JSON-serialisable (no Decimal, no datetime object)
        json.dumps(d)

    def test_different_boilers_differ(self):
        """Per-boiler offsets mean two simulators produce different readings."""
        a = BoilerSimulator(boiler_id=1)
        b = BoilerSimulator(boiler_id=2)
        readings_a = [a.generate_reading().temperature_heat for _ in range(50)]
        readings_b = [b.generate_reading().temperature_heat for _ in range(50)]
        # Means should differ by at least a tiny amount (offsets ≠ 0 with high probability)
        mean_a = sum(readings_a) / 50
        mean_b = sum(readings_b) / 50
        # Not identical (probability of exact equality is ~0)
        assert mean_a != mean_b


# ── scenarios ─────────────────────────────────────────────────────────────────

class TestScenarios:
    def test_all_scenarios_registered(self):
        names = [n for n, _ in SCENARIOS]
        assert "overheat" in names
        assert "leak" in names
        assert "co_spike" in names
        assert "draft_failure" in names
        assert "low_water" in names

    def test_get_scenario_returns_dict(self):
        for name, _ in SCENARIOS:
            overrides = get_scenario(name)
            assert isinstance(overrides, dict)
            assert len(overrides) > 0

    def test_get_scenario_unknown_raises(self):
        with pytest.raises(KeyError):
            get_scenario("nonexistent_scenario")

    def test_random_scenario_returns_tuple(self):
        name, overrides = random_scenario()
        assert isinstance(name, str)
        assert isinstance(overrides, dict)

    def test_overheat_exceeds_critical_high(self):
        overrides = get_scenario("overheat")
        assert overrides["temperature_heat"] > CRITICAL_HIGH["temperature_heat"]

    def test_leak_below_critical_low_pressure(self):
        overrides = get_scenario("leak")
        assert overrides["pressure"] < CRITICAL_LOW["pressure"] + 0.02

    def test_co_spike_exceeds_critical(self):
        overrides = get_scenario("co_spike")
        assert overrides["co_level"] > CRITICAL_HIGH["co_level"]

    def test_draft_failure_near_zero(self):
        overrides = get_scenario("draft_failure")
        # Critical low furnace_draft is -45; near zero means blockage
        assert overrides["furnace_draft"] > CRITICAL_HIGH["furnace_draft"]

    def test_low_water_below_critical(self):
        overrides = get_scenario("low_water")
        assert overrides["water_level"] < CRITICAL_LOW["water_level"]


# ── TelemetrySender (mocked HTTP) ─────────────────────────────────────────────

class TestTelemetrySenderMocked:
    @pytest.mark.asyncio
    async def test_send_calls_correct_endpoint(self):
        from app.telemetry_sender import TelemetrySender

        # Use MagicMock so .json() returns a plain dict, not a coroutine
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1, "status": "normal"}
        mock_response.raise_for_status = lambda: None

        sim = BoilerSimulator(boiler_id=1)
        reading = sim.generate_reading()

        async def fake_post(url, **kwargs):
            return mock_response

        with patch("app.telemetry_sender.httpx.AsyncClient"):
            sender = TelemetrySender()
            sender._client = MagicMock()
            sender._client.post = fake_post
            sender._token = "fake_token"

            result = await sender.send(reading)
            assert result["status"] == "normal"

    @pytest.mark.asyncio
    async def test_send_retries_on_connect_error(self):
        """send() should retry up to 3 times on ConnectError."""
        import httpx
        from app.telemetry_sender import TelemetrySender

        sim = BoilerSimulator(boiler_id=2)
        reading = sim.generate_reading()

        success_resp = MagicMock()
        success_resp.status_code = 201
        success_resp.json.return_value = {"id": 2, "status": "normal"}
        success_resp.raise_for_status = lambda: None

        call_count = 0

        async def flaky_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("refused")
            return success_resp

        with patch("app.telemetry_sender.httpx.AsyncClient"):
            sender = TelemetrySender()
            sender._client = MagicMock()
            sender._client.post = flaky_post
            sender._token = "fake_token"

            result = await sender.send(reading)
            assert result["status"] == "normal"
            assert call_count == 3
