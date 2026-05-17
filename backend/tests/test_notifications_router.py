"""Integration tests for the /api/v1/notifications router."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _get_admin_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await _get_admin_token(client)
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
async def test_send_test_email_success(auth_client):
    """POST /notifications/test-email returns 200 when SMTP succeeds."""
    with patch(
        "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        mock_send.return_value = None
        resp = await auth_client.post(
            "/api/v1/notifications/test-email",
            json={"to": "user@mailtrap.io", "subject": "Test", "body": "Hello"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_send_test_email_smtp_failure(auth_client):
    """POST /notifications/test-email returns 502 when SMTP fails."""
    with patch(
        "app.services.email_service.aiosmtplib.send",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        resp = await auth_client.post(
            "/api/v1/notifications/test-email",
            json={"to": "user@mailtrap.io", "subject": "Test", "body": "Hello"},
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_send_test_email_unauthorized():
    """POST /notifications/test-email without token returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/notifications/test-email",
            json={"to": "user@mailtrap.io", "subject": "Test", "body": "Hello"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_distribute_payslips_bad_period(auth_client):
    """POST /notifications/payslips/distribute with invalid period returns 422."""
    resp = await auth_client.post(
        "/api/v1/notifications/payslips/distribute",
        json={"period_code": "not-a-date"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_event_alarm(auth_client):
    """POST /notifications/events/alarm dispatches without error."""
    with patch(
        "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        mock_send.return_value = None
        resp = await auth_client.post(
            "/api/v1/notifications/events/alarm",
            json={
                "boiler_name": "Котельная №1",
                "parameter_name": "temperature_heat",
                "value": "130",
                "threshold_kind": "critical",
                "detected_at": "2026-05-17T10:00:00",
                "request_number": "REQ-20260517-000001",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dispatched"
