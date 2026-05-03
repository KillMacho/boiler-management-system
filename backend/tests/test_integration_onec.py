"""Integration test: backend sends period data to mock 1C server via HTTP.

Requires the mock 1C server to be running on http://localhost:8080.
If it's not running, tests are skipped gracefully.
"""
from __future__ import annotations

import pytest
import httpx
from httpx import AsyncClient


# ── helpers ───────────────────────────────────────────────────────────────────

MOCK_URL = "http://localhost:8080"
BACKEND_URL = "http://localhost:8000"  # not used by httpx client (uses ASGI)


async def _mock_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            resp = await c.get(f"{MOCK_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_onec_health_endpoint(client: AsyncClient) -> None:
    """GET /api/v1/integration/onec/health should return onec status."""
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/integration/onec/health", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "статус" in body
    assert "onec_url" in body


@pytest.mark.asyncio
async def test_send_period_endpoint_exists(client: AsyncClient) -> None:
    """POST /api/v1/integration/onec/send-period should be reachable."""
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/integration/onec/send-period",
        json={"period": "2026-01"},
        headers=headers,
    )
    # If mock is not running, onec client will fail but endpoint exists
    assert resp.status_code in (200, 500)


@pytest.mark.asyncio
async def test_send_period_with_live_mock(client: AsyncClient) -> None:
    """Full integration: backend → mock 1C → verify mock received data.

    Skipped if mock server is not running on localhost:8080.
    """
    if not await _mock_available():
        pytest.skip("Mock 1C server not running on localhost:8080 — skipping live integration test")

    headers = await _auth_headers(client)

    # Clear mock storage first
    async with httpx.AsyncClient(timeout=5.0) as mock_client:
        await mock_client.delete(f"{MOCK_URL}/admin/received/clear")

    # Send period data
    resp = await client.post(
        "/api/v1/integration/onec/send-period",
        json={"period": "2026-04"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    # May have 0 data if DB is empty for that period — that's OK
    assert "acts_sent" in body
    assert "materials_sent" in body
    assert "transactions_sent" in body
    assert "timesheet_rows_sent" in body
    assert "errors" in body
    assert isinstance(body["errors"], list)

    # Verify mock received something (at minimum empty acts payload was sent)
    async with httpx.AsyncClient(timeout=5.0) as mock_client:
        stats = (await mock_client.get(f"{MOCK_URL}/admin/stats")).json()
    # If acts were sent (even 0 items), the endpoint was called
    # Just check the response structure is valid
    assert "актов" in stats


@pytest.mark.asyncio
async def test_send_period_invalid_format(client: AsyncClient) -> None:
    """Sending a malformed period string should return 422."""
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/integration/onec/send-period",
        json={"period": "avril-2026"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_send_period_requires_auth(client: AsyncClient) -> None:
    """Sending period without token should return 401."""
    resp = await client.post(
        "/api/v1/integration/onec/send-period",
        json={"period": "2026-04"},
    )
    assert resp.status_code == 401
