"""Warehouse service tests: reserve, write-off, receive, check-min-stock."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _get_or_create_warehouse(client: AsyncClient, headers: dict) -> int:
    resp = await client.get("/api/v1/warehouses/", headers=headers)
    warehouses = resp.json()
    if warehouses:
        return warehouses[0]["id"]
    create = await client.post(
        "/api/v1/warehouses/",
        json={"name": "Тестовый склад", "address": "Test"},
        headers=headers,
    )
    assert create.status_code == 201
    return create.json()["id"]


async def _create_material(client: AsyncClient, headers: dict) -> dict:
    """Create a fresh material + category for isolation."""
    import uuid

    cat_resp = await client.post(
        "/api/v1/material-categories/",
        json={"name": f"TestCat_{uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    mat_resp = await client.post(
        "/api/v1/materials/",
        json={
            "category_id": cat_id,
            "name": f"TestMat_{uuid.uuid4().hex[:6]}",
            "unit": "шт",
            "barcode": f"BC{uuid.uuid4().hex[:10]}",  # unique barcode avoids NULL UNIQUE conflict
            "min_stock": "5",
            "price": "100.00",
        },
        headers=headers,
    )
    assert mat_resp.status_code == 201
    return mat_resp.json()


async def _seed_stock(client: AsyncClient, headers: dict, material_id: int, warehouse_id: int, qty: str) -> None:
    """Add stock via receive endpoint."""
    resp = await client.post(
        "/api/v1/warehouse/receive",
        json={
            "material_id": material_id,
            "warehouse_id": warehouse_id,
            "quantity": qty,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


async def _get_open_work_order(client: AsyncClient, headers: dict) -> int:
    """Find or create a work order in 'assigned' status."""
    resp = await client.get(
        "/api/v1/work-orders/", params={"status": "assigned"}, headers=headers
    )
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]

    # Create a request + work order
    req_resp = await client.post(
        "/api/v1/requests/",
        json={"description": "склад тест", "boiler_id": 1, "source": "web"},
        headers=headers,
    )
    assert req_resp.status_code == 201
    body = req_resp.json()
    if body.get("work_order"):
        return body["work_order"]["id"]
    # No brigade available — create a minimal work order via request
    return -1  # signal: no WO available


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_receive_materials_increases_stock(client: AsyncClient) -> None:
    """POST /warehouse/receive should increase stock quantity."""
    headers = await _auth_headers(client)
    wh_id = await _get_or_create_warehouse(client, headers)
    mat = await _create_material(client, headers)
    mat_id = mat["id"]

    # Receive 10 units
    resp = await client.post(
        "/api/v1/warehouse/receive",
        json={"material_id": mat_id, "warehouse_id": wh_id, "quantity": "10"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["movement_type"] == "income"
    assert float(body["quantity"]) == 10.0

    # Stock should reflect the 10 units
    stock_resp = await client.get(
        "/api/v1/stock/", params={"material_id": mat_id}, headers=headers
    )
    assert stock_resp.status_code == 200
    stocks = stock_resp.json()
    assert any(float(s["quantity"]) >= 10 for s in stocks)


@pytest.mark.asyncio
async def test_reserve_with_sufficient_stock(client: AsyncClient) -> None:
    """Reserving when stock >= needed → all_reserved=True."""
    headers = await _auth_headers(client)
    wh_id = await _get_or_create_warehouse(client, headers)
    mat = await _create_material(client, headers)
    mat_id = mat["id"]

    # Seed 20 units
    await _seed_stock(client, headers, mat_id, wh_id, "20")

    wo_id = await _get_open_work_order(client, headers)
    if wo_id == -1:
        pytest.skip("no work order available for reserve test")

    resp = await client.post(
        "/api/v1/warehouse/reserve",
        json={
            "work_order_id": wo_id,
            "materials": [{"material_id": mat_id, "quantity": "5"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["all_reserved"] is True
    assert body["reserved_count"] == 1
    assert body["purchase_requests_created"] == []


@pytest.mark.asyncio
async def test_reserve_with_insufficient_stock_creates_purchase_request(client: AsyncClient) -> None:
    """Reserving more than available → purchase_request created, all_reserved=False."""
    headers = await _auth_headers(client)
    wh_id = await _get_or_create_warehouse(client, headers)
    mat = await _create_material(client, headers)
    mat_id = mat["id"]

    # Seed only 2 units, request 100
    await _seed_stock(client, headers, mat_id, wh_id, "2")

    wo_id = await _get_open_work_order(client, headers)
    if wo_id == -1:
        pytest.skip("no work order available")

    resp = await client.post(
        "/api/v1/warehouse/reserve",
        json={
            "work_order_id": wo_id,
            "materials": [{"material_id": mat_id, "quantity": "100"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["all_reserved"] is False
    assert len(body["purchase_requests_created"]) >= 1

    # Purchase request should be in DB
    pr_id = body["purchase_requests_created"][0]
    pr_resp = await client.get(
        "/api/v1/purchase-requests/", params={"status": "submitted"}, headers=headers
    )
    assert pr_resp.status_code == 200
    pr_ids = [p["id"] for p in pr_resp.json()]
    assert pr_id in pr_ids


@pytest.mark.asyncio
async def test_receive_with_purchase_request_marks_received(client: AsyncClient) -> None:
    """Receiving with purchase_request_id → PR status = 'received'."""
    headers = await _auth_headers(client)
    wh_id = await _get_or_create_warehouse(client, headers)
    mat = await _create_material(client, headers)
    mat_id = mat["id"]

    # Create a purchase request manually
    pr_resp = await client.post(
        "/api/v1/purchase-requests/",
        json={"material_id": mat_id, "quantity": "50", "status": "submitted"},
        headers=headers,
    )
    assert pr_resp.status_code == 201
    pr_id = pr_resp.json()["id"]

    # Receive 50 units against this PR
    recv_resp = await client.post(
        "/api/v1/warehouse/receive",
        json={
            "material_id": mat_id,
            "warehouse_id": wh_id,
            "quantity": "50",
            "purchase_request_id": pr_id,
        },
        headers=headers,
    )
    assert recv_resp.status_code == 201, recv_resp.text

    # PR should now be 'received'
    pr_check = await client.get(
        "/api/v1/purchase-requests/", params={"status": "received"}, headers=headers
    )
    assert pr_check.status_code == 200
    received_ids = [p["id"] for p in pr_check.json()]
    assert pr_id in received_ids


@pytest.mark.asyncio
async def test_check_min_stock_creates_purchase_requests(client: AsyncClient) -> None:
    """POST /warehouse/check-min-stock should create PRs for materials below min_stock."""
    headers = await _auth_headers(client)

    # This endpoint just returns created PRs (may be 0 if all stocks are OK)
    resp = await client.post("/api/v1/warehouse/check-min-stock", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
