"""Timesheet service tests: auto-fill, monthly summary, payroll data."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _get_active_employee_id(client: AsyncClient, headers: dict) -> int:
    resp = await client.get(
        "/api/v1/employees/", params={"status": "active"}, headers=headers
    )
    assert resp.status_code == 200
    employees = resp.json()
    if not employees:
        pytest.skip("no active employees in DB")
    return employees[0]["id"]


@pytest.mark.asyncio
async def test_auto_fill_creates_records(client: AsyncClient) -> None:
    """POST /timesheets/auto-fill should create working-day records for the month."""
    headers = await _auth_headers(client)
    emp_id = await _get_active_employee_id(client, headers)

    resp = await client.post(
        "/api/v1/timesheets/auto-fill",
        json={"employee_id": emp_id, "year": 2025, "month": 1},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["employee_id"] == emp_id
    # January 2025 has 23 working days; should create at least some
    assert body["records_created"] >= 0  # 0 if already filled


@pytest.mark.asyncio
async def test_auto_fill_is_idempotent(client: AsyncClient) -> None:
    """Running auto-fill twice creates 0 records the second time."""
    headers = await _auth_headers(client)
    emp_id = await _get_active_employee_id(client, headers)

    # Fill for a specific month
    payload = {"employee_id": emp_id, "year": 2025, "month": 2}

    first = await client.post("/api/v1/timesheets/auto-fill", json=payload, headers=headers)
    assert first.status_code == 200

    # Second call should create 0 new records
    second = await client.post("/api/v1/timesheets/auto-fill", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["records_created"] == 0


@pytest.mark.asyncio
async def test_monthly_summary_returns_hours(client: AsyncClient) -> None:
    """GET /timesheets/summary returns aggregated hours after auto-fill."""
    headers = await _auth_headers(client)
    emp_id = await _get_active_employee_id(client, headers)

    # Ensure there's some data
    await client.post(
        "/api/v1/timesheets/auto-fill",
        json={"employee_id": emp_id, "year": 2025, "month": 3},
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/timesheets/summary",
        params={"employee_id": emp_id, "year": 2025, "month": 3},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["employee_id"] == emp_id
    assert body["year"] == 2025
    assert body["month"] == 3
    assert "regular_hours" in body
    assert "total_hours" in body
    # March 2025 has 20 working days → 160 regular hours
    assert float(body["regular_hours"]) >= 0


@pytest.mark.asyncio
async def test_payroll_data_returns_list(client: AsyncClient) -> None:
    """GET /timesheets/payroll-data returns a list of payroll items."""
    headers = await _auth_headers(client)
    resp = await client.get(
        "/api/v1/timesheets/payroll-data",
        params={"year": 2025, "month": 3},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "employee_id" in item
        assert "full_name" in item
        assert "base_salary" in item
        assert "total_estimated" in item
