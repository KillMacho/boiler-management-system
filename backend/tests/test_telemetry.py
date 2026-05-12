"""Telemetry intake tests: normal, critical threshold breach, deduplication."""
from __future__ import annotations

import asyncio
import pytest
from httpx import AsyncClient

# Boiler 15 used here to avoid interfering with other tests.
# Critical threshold for temperature_heat in test data: max_critical=120°C.
BOILER_ID = 15

NORMAL_PAYLOAD = {
    "boiler_id": BOILER_ID,
    "temperature_heat": 75.0,
    "pressure": 0.4,
    "co_level": 10.0,
    "gas_flow": 50.0,
    "water_level": 250.0,
    "temperature_return": 55.0,
    "furnace_draft": -20.0,
}

CRITICAL_PAYLOAD = {**NORMAL_PAYLOAD, "temperature_heat": 130.0}


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_normal_telemetry(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/telemetry/", json=NORMAL_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["boiler_id"] == BOILER_ID
    assert body["status"] == "normal"
    assert body["auto_request_id"] is None


@pytest.mark.asyncio
async def test_critical_telemetry_creates_auto_request(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    # Count open Авария requests for this boiler before sending
    before_resp = await client.get(
        "/api/v1/requests/",
        params={"boiler_id": BOILER_ID, "source": "monitoring"},
        headers=headers,
    )
    assert before_resp.status_code == 200
    before_count = sum(
        1 for r in before_resp.json()
        if r["status"] not in ("completed", "closed", "cancelled")
    )

    # Send critical telemetry
    resp = await client.post("/api/v1/telemetry/", json=CRITICAL_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "critical"
    assert len(body["breaches"]) > 0

    # After the critical reading there must be exactly 1 open Авария for this boiler
    after_resp = await client.get(
        "/api/v1/requests/",
        params={"boiler_id": BOILER_ID, "source": "monitoring"},
        headers=headers,
    )
    assert after_resp.status_code == 200
    after_open = [
        r for r in after_resp.json()
        if r["status"] not in ("completed", "closed", "cancelled")
    ]
    if before_count == 0:
        # Fresh state: auto-request should have been created
        assert len(after_open) == 1
        assert body["auto_request_id"] is not None
    else:
        # Already had open avaria — dedup kicked in
        assert body["auto_request_id"] is None
        assert len(after_open) == before_count


@pytest.mark.asyncio
async def test_dedup_second_critical(client: AsyncClient) -> None:
    # First critical to ensure there is an open avaria
    first = await client.post("/api/v1/telemetry/", json=CRITICAL_PAYLOAD)
    assert first.status_code == 201

    # Second critical — dedup must return auto_request_id=None
    second = await client.post("/api/v1/telemetry/", json=CRITICAL_PAYLOAD)
    assert second.status_code == 201, second.text
    assert second.json()["auto_request_id"] is None


@pytest.mark.asyncio
async def test_telemetry_batch(client: AsyncClient) -> None:
    batch = [
        {**NORMAL_PAYLOAD, "boiler_id": 14, "temperature_heat": 70.0},
        {**NORMAL_PAYLOAD, "boiler_id": 13, "temperature_heat": 68.0},
    ]
    resp = await client.post("/api/v1/telemetry/batch", json=batch)
    assert resp.status_code == 201, resp.text
    items = resp.json()
    assert len(items) == 2
    assert all(i["status"] == "normal" for i in items)


@pytest.mark.asyncio
async def test_telemetry_latest(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    # Send a reading first to ensure there is data
    await client.post("/api/v1/telemetry/", json=NORMAL_PAYLOAD)
    resp = await client.get(f"/api/v1/telemetry/{BOILER_ID}/latest", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["boiler_id"] == BOILER_ID


@pytest.mark.asyncio
async def test_telemetry_history(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get(
        f"/api/v1/telemetry/{BOILER_ID}/history",
        params={"limit": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_concurrent_telemetry_15_requests(client: AsyncClient) -> None:
    """Stress test: 15 parallel POST requests (simulating burst from simulator)."""
    # Use same boiler_id for all, different temps, staggered timestamps
    from datetime import datetime, timedelta, timezone
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)

    payloads = [
        {
            **NORMAL_PAYLOAD,
            "boiler_id": BOILER_ID,
            "temperature_heat": 70.0 + (i * 0.1),
            "timestamp": (base_time + timedelta(milliseconds=i)).isoformat(),  # ISO string
        }
        for i in range(15)
    ]

    async def send_one(payload: dict) -> tuple[int, str]:
        resp = await client.post("/api/v1/telemetry/", json=payload)
        return resp.status_code, resp.json().get("status", "error")

    results = await asyncio.gather(*[send_one(p) for p in payloads])

    # All 15 requests must succeed
    assert len(results) == 15, f"Expected 15 results, got {len(results)}"
    for i, (status_code, status_str) in enumerate(results):
        assert status_code == 201, f"Request {i}: Expected 201, got {status_code}"
        assert status_str in ("normal", "warning", "critical"), f"Request {i}: Invalid status '{status_str}'"


