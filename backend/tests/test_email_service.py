"""Tests for EmailService.

Uses unittest.mock to avoid real SMTP connections.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_service import EmailService
from app.config import get_settings


@pytest.fixture
def svc():
    return EmailService(get_settings())


@pytest.mark.asyncio
async def test_send_email_success(svc):
    """send_email returns True when aiosmtplib.send succeeds."""
    with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        ok = await svc.send_email(
            to="test@mailtrap.io",
            subject="Test",
            body_text="Hello",
        )
    assert ok is True
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_failure(svc):
    """send_email returns False and logs error on SMTP exception."""
    with patch(
        "app.services.email_service.aiosmtplib.send",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        ok = await svc.send_email(
            to="test@mailtrap.io",
            subject="Test",
            body_text="Hello",
        )
    assert ok is False


@pytest.mark.asyncio
async def test_send_email_with_html(svc):
    """send_email accepts optional HTML body."""
    with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        ok = await svc.send_email(
            to="test@mailtrap.io",
            subject="HTML test",
            body_text="Plain",
            body_html="<b>Bold</b>",
        )
    assert ok is True


@pytest.mark.asyncio
async def test_send_bulk(svc):
    """send_bulk returns correct counters."""
    call_count = 0

    async def fake_send(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("fail")

    with patch("app.services.email_service.aiosmtplib.send", side_effect=fake_send):
        result = await svc.send_bulk(
            recipients=["a@t.io", "b@t.io", "c@t.io"],
            subject="Bulk",
            body_text="msg",
        )

    assert result["sent"] == 2
    assert result["failed"] == 1
    assert "b@t.io" in result["errors"]
