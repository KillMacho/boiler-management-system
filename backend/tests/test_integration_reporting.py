"""Integration tests: backend reporting endpoints + optional live mock EDO.

If mock EDO is not running on localhost:8081, live tests are skipped gracefully.
Endpoint structure tests always run (they hit the backend ASGI directly).
"""
from __future__ import annotations

import pytest
import httpx
from httpx import AsyncClient


MOCK_EDO_URL = "http://localhost:8081"


async def _edo_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            resp = await c.get(f"{MOCK_EDO_URL}/health")
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


# ── endpoint availability ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reporting_list_endpoint(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/reporting/list", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_reporting_list_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reporting/list")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_invalid_period_returns_422(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "6-NDFL", "period": "2026-04"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_szv_stazh_wrong_period_format(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "SZV-STAZH", "period": "2026-Q1"},
        headers=headers,
    )
    assert resp.status_code == 422


# ── generate endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_6ndfl_creates_report(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "6-NDFL", "period": "2026-Q1"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_type"] == "6-NDFL"
    assert body["period"] == "2026-Q1"
    assert body["size_bytes"] > 0
    assert "id" in body


@pytest.mark.asyncio
async def test_generate_rsv_creates_report(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "RSV", "period": "2026-Q1"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "RSV"


@pytest.mark.asyncio
async def test_generate_4fss_creates_report(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "4-FSS", "period": "2026-Q1"},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_generate_szv_stazh_creates_report(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "SZV-STAZH", "period": "2026"},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    # Generate first
    gen = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "RSV", "period": "2026-Q2"},
        headers=headers,
    )
    report_id = gen.json()["id"]

    resp = await client.get(f"/api/v1/reporting/{report_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == report_id
    assert body["report_type"] == "RSV"


@pytest.mark.asyncio
async def test_get_report_404(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/reporting/99999999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_report(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    gen = await client.post(
        "/api/v1/reporting/generate",
        json={"report_type": "4-FSS", "period": "2026-Q2"},
        headers=headers,
    )
    report_id = gen.json()["id"]
    resp = await client.get(f"/api/v1/reporting/{report_id}/download", headers=headers)
    assert resp.status_code == 200
    assert b"<?xml" in resp.content


# ── submit (live EDO required) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_with_live_edo(client: AsyncClient) -> None:
    """Full end-to-end: generate → submit → verify in mock EDO admin."""
    if not await _edo_available():
        pytest.skip("Mock EDO not running on localhost:8081")

    headers = await _auth_headers(client)

    # Clear EDO storage first
    async with httpx.AsyncClient(timeout=5.0) as edo:
        await edo.delete(f"{MOCK_EDO_URL}/admin/clear")

    resp = await client.post(
        "/api/v1/reporting/submit",
        json={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["submission_id"].startswith("SUB-")
    assert body["receipt_number"].startswith("КВТ-")
    assert body["edo_status"] == "accepted"

    # Verify mock EDO received it
    async with httpx.AsyncClient(timeout=5.0) as edo:
        all_resp = await edo.get(f"{MOCK_EDO_URL}/admin/all")
    submissions = all_resp.json()
    assert len(submissions) >= 1
    assert submissions[0]["report_type"] == "6-NDFL"


@pytest.mark.asyncio
async def test_submit_without_edo_returns_502(client: AsyncClient) -> None:
    """When EDO is unavailable, submit returns 502."""
    if await _edo_available():
        pytest.skip("Mock EDO IS running — this test needs it offline")

    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/reporting/submit",
        json={"report_type": "RSV", "period": "2026-Q1", "inn": "7700000001"},
        headers=headers,
    )
    assert resp.status_code == 502
