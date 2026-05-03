"""Tests for OneCClient: payload formatting, HTTP calls, error handling (mocked HTTP)."""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.onec_client import OneCClient


def _make_client() -> OneCClient:
    return OneCClient(
        base_url="http://mock-1c:8080",
        username="app_user",
        password="password123",
    )


def _ok_response(body: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.raise_for_status = lambda: None
    return resp


def _error_response(status: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=resp
    )
    return resp


# ── send_acts ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_acts_posts_correct_url():
    client = _make_client()
    acts = [{"номер_акта": "АКТ-0001", "дата": "2026-04-15", "котельная_id": 1,
              "котельная_наименование": "К1", "бригада": "Б1", "сумма": 1000.0, "материалы": []}]
    expected_response = {"статус": "ok", "получено_актов": 1, "проведено_актов": 1,
                         "номера_документов_1с": ["00000001"], "сообщение": "ok"}
    posted = {}

    async def fake_post(url, json=None, **kwargs):
        posted["url"] = url
        posted["json"] = json
        return _ok_response(expected_response)

    with patch.object(type(client._client()), "__aenter__") as mock_ctx:
        mock_instance = AsyncMock()
        mock_instance.post = fake_post
        mock_ctx.return_value = mock_instance
        # Use a direct async context manager mock
        async with client._client() as _:
            pass

    # Simpler: patch httpx.AsyncClient directly
    async def run():
        async def fake_post_inner(url, json=None, **kwargs):
            posted["url"] = url
            posted["json"] = json
            return _ok_response(expected_response)

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = fake_post_inner
            MockClient.return_value = instance

            result = await client.send_acts("2026-04", acts)

        return result

    result = await run()
    assert result["статус"] == "ok"
    assert posted["url"] == "/hs/boiler/acts"
    assert posted["json"]["период"] == "2026-04"
    assert len(posted["json"]["акты"]) == 1


@pytest.mark.asyncio
async def test_send_acts_payload_has_cyrillic_keys():
    client = _make_client()
    posted_json = {}

    async def fake_post(url, json=None, **kwargs):
        posted_json.update(json or {})
        return _ok_response({"статус": "ok", "получено_актов": 0, "проведено_актов": 0,
                              "номера_документов_1с": [], "сообщение": "ok"})

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance
        await client.send_acts("2026-04", [])

    assert "период" in posted_json
    assert "акты" in posted_json


# ── send_materials ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_materials_correct_payload():
    client = _make_client()
    movements = [
        {
            "тип_операции": "списание",
            "дата": "2026-04-15",
            "номенклатура": "Прокладка",
            "количество": 5,
            "сумма": 1000.0,
            "наряд_номер": "Н-001",
            "котельная_наименование": "К1",
        }
    ]
    posted_json = {}

    async def fake_post(url, json=None, **kwargs):
        posted_json.update(json or {})
        return _ok_response({"статус": "ok", "получено": 1, "проведено": 1})

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance
        result = await client.send_materials("2026-04", movements)

    assert result["статус"] == "ok"
    assert posted_json["период"] == "2026-04"
    assert "движения_материалов" in posted_json
    assert len(posted_json["движения_материалов"]) == 1


# ── send_transactions ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_transactions_correct_payload():
    client = _make_client()
    transactions = [
        {
            "дата": "2026-04-30",
            "дебет_счёт": "20",
            "кредит_счёт": "10",
            "сумма": 5000.0,
            "содержание": "Списание",
        }
    ]
    posted_json = {}

    async def fake_post(url, json=None, **kwargs):
        posted_json.update(json or {})
        return _ok_response({"статус": "ok", "проведено_проводок": 1})

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance
        result = await client.send_transactions("2026-04", transactions)

    assert result["проведено_проводок"] == 1
    assert "проводки" in posted_json


# ── send_timesheet ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_timesheet_correct_payload():
    client = _make_client()
    rows = [{"сотрудник_id": 1, "сотрудник_фио": "Иванов И.И.",
              "обычные_часы": 168, "сверхурочные": 0, "отпуск": 0, "больничный": 0}]
    posted_json = {}

    async def fake_post(url, json=None, **kwargs):
        posted_json.update(json or {})
        return _ok_response({"статус": "ok", "получено_строк": 1})

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance
        result = await client.send_timesheet("2026-04", rows)

    assert result["получено_строк"] == 1
    assert "табель" in posted_json


# ── send_payslip_request ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_payslip_request_correct_payload():
    client = _make_client()
    posted_json = {}

    async def fake_post(url, json=None, **kwargs):
        posted_json.update(json or {})
        return _ok_response({
            "статус": "ok",
            "сформировано": 5,
            "расчётные_листки": [],
        })

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance
        result = await client.send_payslip_request("2026-04")

    assert result["сформировано"] == 5
    assert posted_json["период"] == "2026-04"
    assert posted_json["запрос"] == "сформировать_расчётные_листки"


# ── error handling ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_acts_raises_on_401():
    client = _make_client()

    async def fake_post(url, json=None, **kwargs):
        return _error_response(401)

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await client.send_acts("2026-04", [])


@pytest.mark.asyncio
async def test_send_acts_raises_on_500():
    client = _make_client()

    async def fake_post(url, json=None, **kwargs):
        return _error_response(500)

    with patch("httpx.AsyncClient") as MockClient:
        instance = MagicMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = fake_post
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await client.send_acts("2026-04", [])
