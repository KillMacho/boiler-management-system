"""Tests for EDOClient: payload formatting, HTTP calls, error handling (mocked HTTP)."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.edo_client import EDOClient


def _make_client() -> EDOClient:
    return EDOClient(base_url="http://mock-edo:8081", api_key="test_key")


def _ok(body: dict, code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = code
    r.json.return_value = body
    r.raise_for_status = lambda: None
    return r


def _err(code: int) -> MagicMock:
    r = MagicMock()
    r.status_code = code
    r.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=r
    )
    return r


# ── submit_report ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_report_sends_multipart(tmp_path):
    xml_file = tmp_path / "test.xml"
    xml_file.write_text('<Файл/>', encoding="utf-8")

    client = _make_client()
    expected = {
        "submission_id": "SUB-2026-05-01-00001",
        "receipt_number": "КВТ-7700-2026-05-01-00001",
        "status": "accepted",
        "received_at": "2026-05-01T10:00:00+00:00",
        "estimated_processing_minutes": 15,
        "message": "Принято",
    }
    posted_kwargs = {}

    async def fake_post(url, **kwargs):
        posted_kwargs.update({"url": url, **kwargs})
        return _ok(expected)

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance

        result = await client.submit_report(
            filepath=str(xml_file),
            report_type="6-NDFL",
            period="2026-Q1",
            inn="7700000001",
        )

    assert result["submission_id"] == "SUB-2026-05-01-00001"
    assert posted_kwargs["url"] == "/api/v1/submission/upload"
    assert "data" in posted_kwargs
    assert posted_kwargs["data"]["report_type"] == "6-NDFL"
    assert posted_kwargs["data"]["inn"] == "7700000001"
    assert "files" in posted_kwargs


@pytest.mark.asyncio
async def test_submit_report_file_not_found():
    client = _make_client()
    with pytest.raises(FileNotFoundError):
        await client.submit_report(
            filepath="/nonexistent/path/report.xml",
            report_type="RSV",
            period="2026-Q1",
            inn="7700000001",
        )


@pytest.mark.asyncio
async def test_submit_report_raises_on_401(tmp_path):
    xml_file = tmp_path / "test.xml"
    xml_file.write_text('<Файл/>', encoding="utf-8")
    client = _make_client()

    async def fake_post(url, **kwargs):
        return _err(401)

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await client.submit_report(str(xml_file), "RSV", "2026-Q1", "7700000001")


# ── check_status ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_status_returns_dict():
    client = _make_client()
    expected = {
        "submission_id": "SUB-001",
        "status": "processing",
        "history": [],
    }
    gotten_url = {}

    async def fake_get(url, **kwargs):
        gotten_url["url"] = url
        return _ok(expected)

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = fake_get
        MockClient.return_value = instance

        result = await client.check_status("SUB-001")

    assert result["status"] == "processing"
    assert gotten_url["url"] == "/api/v1/status/SUB-001"


# ── list_submissions ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_submissions_passes_params():
    client = _make_client()
    gotten_params = {}

    async def fake_get(url, params=None, **kwargs):
        gotten_params.update(params or {})
        return _ok([])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get = fake_get
        MockClient.return_value = instance

        result = await client.list_submissions("7700000001", "2026-Q1")

    assert gotten_params["inn"] == "7700000001"
    assert gotten_params["period"] == "2026-Q1"
    assert result == []


# ── API key header ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_key_in_default_headers(tmp_path):
    """EDOClient must send X-API-Key in every request."""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text('<Файл/>', encoding="utf-8")
    client = _make_client()

    captured_headers = {}

    async def fake_post(url, **kwargs):
        return _ok({"submission_id": "X", "receipt_number": "Y", "status": "accepted",
                     "received_at": "T", "estimated_processing_minutes": 1, "message": "ok"})

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance

        # Check that AsyncClient was constructed with X-API-Key header
        await client.submit_report(str(xml_file), "4-FSS", "2026-Q1", "7700000001")
        call_kwargs = MockClient.call_args[1]
        assert call_kwargs["headers"]["X-API-Key"] == "test_key"
