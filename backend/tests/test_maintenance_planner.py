"""Maintenance planner tests: generate plan, upcoming, approve."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_generate_plan_creates_schedule(client: AsyncClient) -> None:
    # Генерируем план на 90 дней вперёд — ожидаем schedule_id и количество созданных позиций
    headers = await _auth_headers(client)

    today = date.today()
    period_start = today.isoformat()
    period_end = (today + timedelta(days=90)).isoformat()

    resp = await client.post(
        "/api/v1/maintenance/generate-plan",
        json={"period_start": period_start, "period_end": period_end},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "schedule_id" in body
    assert body["schedule_id"] > 0
    assert "items_created" in body
    assert isinstance(body["items_created"], int)
    assert isinstance(body["brigades_assigned"], int)


@pytest.mark.asyncio
async def test_get_plan_items_for_schedule(client: AsyncClient) -> None:
    """GET /maintenance/plan/{schedule_id} returns plan items."""
    headers = await _auth_headers(client)

    today = date.today()
    create_resp = await client.post(
        "/api/v1/maintenance/generate-plan",
        json={
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=60)).isoformat(),
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    schedule_id = create_resp.json()["schedule_id"]

    items_resp = await client.get(
        f"/api/v1/maintenance/plan/{schedule_id}", headers=headers
    )
    assert items_resp.status_code == 200
    assert isinstance(items_resp.json(), list)


@pytest.mark.asyncio
async def test_upcoming_maintenance_returns_list(client: AsyncClient) -> None:
    """GET /maintenance/upcoming returns a list of upcoming regulations."""
    headers = await _auth_headers(client)
    resp = await client.get(
        "/api/v1/maintenance/upcoming", params={"days_ahead": 30}, headers=headers
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_approve_plan_item_requires_existing_item(client: AsyncClient) -> None:
    """PUT /maintenance/plan-item/99999999/approve should 404 for nonexistent item."""
    headers = await _auth_headers(client)
    resp = await client.put(
        "/api/v1/maintenance/plan-item/99999999/approve", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_plan_item_end_to_end(client: AsyncClient) -> None:
    """Generate a plan, then approve first item — should create a request."""
    headers = await _auth_headers(client)

    # Generate plan for a wide period to capture any existing regulations
    today = date.today()
    create_resp = await client.post(
        "/api/v1/maintenance/generate-plan",
        json={
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=180)).isoformat(),
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    schedule_id = create_resp.json()["schedule_id"]
    items_created = create_resp.json()["items_created"]

    if items_created == 0:
        pytest.skip("No regulations due in period — seed data may not cover this range")

    # Get plan items
    items_resp = await client.get(
        f"/api/v1/maintenance/plan/{schedule_id}", headers=headers
    )
    items = items_resp.json()
    item_id = items[0]["id"]

    # Approve it
    approve_resp = await client.put(
        f"/api/v1/maintenance/plan-item/{item_id}/approve", headers=headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "approved"
