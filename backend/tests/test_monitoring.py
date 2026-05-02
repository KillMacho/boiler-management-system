"""Monitoring endpoints: dashboard status, active alarms, threshold CRUD."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

BOILER_ID = 15  # same boiler as telemetry tests, so cache should have a reading

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
async def test_dashboard_status_returns_all_boilers(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/monitoring/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 15
    ids = {b["boiler_id"] for b in data}
    for expected_id in range(1, 16):
        assert expected_id in ids, f"boiler_id={expected_id} missing from dashboard"


@pytest.mark.asyncio
async def test_dashboard_shows_red_after_critical(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    # Ensure a critical reading is in the StatusCache
    await client.post("/api/v1/telemetry/", json=CRITICAL_PAYLOAD)

    resp = await client.get("/api/v1/monitoring/status", headers=headers)
    assert resp.status_code == 200
    entry = next(b for b in resp.json() if b["boiler_id"] == BOILER_ID)
    # StatusCache or DB fallback — after critical telemetry boiler must be red
    assert entry["status"] in ("red", "critical"), (
        f"Expected red/critical after T=130, got {entry['status']}"
    )


@pytest.mark.asyncio
async def test_active_alarms_nonempty_after_critical(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    # Create at least one critical avaria
    await client.post("/api/v1/telemetry/", json=CRITICAL_PAYLOAD)

    resp = await client.get("/api/v1/monitoring/alarms/active", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # There should be at least one open Авария request
    assert len(data) >= 1
    assert all(r["status"] in ("new", "assigned", "in_progress") for r in data)


@pytest.mark.asyncio
async def test_threshold_crud(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    # Create a threshold for a non-existent boiler_id to avoid conflicts
    payload = {
        "boiler_id": None,  # global
        "parameter_name": "co_level",
        "min_warning": None,
        "max_warning": "50",
        "min_critical": None,
        "max_critical": "100",
    }
    create_resp = await client.post(
        "/api/v1/monitoring/thresholds", json=payload, headers=headers
    )
    assert create_resp.status_code == 201, create_resp.text
    threshold_id = create_resp.json()["id"]

    # Update
    update_resp = await client.put(
        f"/api/v1/monitoring/thresholds/{threshold_id}",
        json={"max_warning": "60"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["max_warning"]) == 60.0

    # Delete
    del_resp = await client.delete(
        f"/api/v1/monitoring/thresholds/{threshold_id}", headers=headers
    )
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = await client.get("/api/v1/monitoring/thresholds", headers=headers)
    ids = [t["id"] for t in list_resp.json()]
    assert threshold_id not in ids
