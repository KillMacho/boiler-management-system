"""Tests for the mock 1C server: all endpoints, auth, storage persistence."""
from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.storage import storage

CLIENT = TestClient(app)

CREDS = base64.b64encode(b"app_user:password123").decode()
AUTH_HEADER = {"Authorization": f"Basic {CREDS}"}
BAD_CREDS = base64.b64encode(b"wrong:wrong").decode()
BAD_HEADER = {"Authorization": f"Basic {BAD_CREDS}"}


@pytest.fixture(autouse=True)
def clear_storage():
    """Reset storage before each test for isolation."""
    storage.clear()
    yield
    storage.clear()


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = CLIENT.get("/health")
    assert resp.status_code == 200
    assert resp.json()["статус"] == "ok"


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_acts_requires_auth():
    resp = CLIENT.post("/hs/boiler/acts", json={
        "период": "2026-04",
        "акты": [],
    })
    assert resp.status_code == 401

def test_acts_rejects_bad_credentials():
    resp = CLIENT.post(
        "/hs/boiler/acts",
        json={"период": "2026-04", "акты": []},
        headers=BAD_HEADER,
    )
    assert resp.status_code == 401

def test_materials_requires_auth():
    resp = CLIENT.post("/hs/boiler/materials", json={
        "период": "2026-04",
        "движения_материалов": [],
    })
    assert resp.status_code == 401

def test_transactions_requires_auth():
    resp = CLIENT.post("/hs/boiler/transactions", json={
        "период": "2026-04",
        "проводки": [],
    })
    assert resp.status_code == 401

def test_timesheet_requires_auth():
    resp = CLIENT.post("/hs/boiler/timesheet", json={
        "период": "2026-04",
        "табель": [],
    })
    assert resp.status_code == 401

def test_payslips_requires_auth():
    resp = CLIENT.post("/hs/boiler/payslips", json={
        "период": "2026-04",
        "запрос": "сформировать_расчётные_листки",
    })
    assert resp.status_code == 401


# ── Acts ──────────────────────────────────────────────────────────────────────

def test_receive_acts_returns_ok():
    payload = {
        "период": "2026-04",
        "акты": [
            {
                "номер_акта": "АКТ-2026-04-0001",
                "дата": "2026-04-15",
                "котельная_id": 5,
                "котельная_наименование": "Котельная №5",
                "бригада": "Бригада №2",
                "сумма": 15000.0,
                "материалы": [
                    {"номенклатура": "Прокладка резиновая", "количество": 5, "цена": 200.0}
                ],
            }
        ],
    }
    resp = CLIENT.post("/hs/boiler/acts", json=payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["статус"] == "ok"
    assert body["получено_актов"] == 1
    assert body["проведено_актов"] == 1
    assert len(body["номера_документов_1с"]) == 1
    assert "2026-04" in body["сообщение"]

def test_receive_acts_stores_in_memory():
    payload = {
        "период": "2026-04",
        "акты": [
            {
                "номер_акта": "АКТ-2026-04-0001",
                "дата": "2026-04-15",
                "котельная_id": 1,
                "котельная_наименование": "Котельная №1",
                "бригада": "Бригада №1",
                "сумма": 5000.0,
                "материалы": [],
            }
        ],
    }
    CLIENT.post("/hs/boiler/acts", json=payload, headers=AUTH_HEADER)
    admin_resp = CLIENT.get("/admin/received/acts")
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert "2026-04" in data
    assert len(data["2026-04"]) == 1

def test_receive_multiple_acts_batches():
    for i in range(3):
        CLIENT.post("/hs/boiler/acts", json={
            "период": "2026-04",
            "акты": [
                {
                    "номер_акта": f"АКТ-2026-04-{i:04d}",
                    "дата": "2026-04-15",
                    "котельная_id": i + 1,
                    "котельная_наименование": f"Котельная №{i+1}",
                    "бригада": "Бригада №1",
                    "сумма": 1000.0 * (i + 1),
                    "материалы": [],
                }
            ],
        }, headers=AUTH_HEADER)
    data = CLIENT.get("/admin/received/acts").json()
    assert len(data["2026-04"]) == 3


# ── Materials ─────────────────────────────────────────────────────────────────

def test_receive_materials_returns_ok():
    payload = {
        "период": "2026-04",
        "движения_материалов": [
            {
                "тип_операции": "списание",
                "дата": "2026-04-15",
                "номенклатура": "Прокладка резиновая",
                "количество": 5,
                "сумма": 1000.0,
                "наряд_номер": "Н-2026-04-0023",
                "котельная_наименование": "Котельная №5",
            }
        ],
    }
    resp = CLIENT.post("/hs/boiler/materials", json=payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["статус"] == "ok"
    assert body["получено"] == 1
    assert body["проведено"] == 1

def test_receive_materials_stores_in_memory():
    payload = {
        "период": "2026-05",
        "движения_материалов": [
            {
                "тип_операции": "поступление",
                "дата": "2026-05-01",
                "номенклатура": "Труба стальная",
                "количество": 10,
                "сумма": 5000.0,
                "наряд_номер": "Н-2026-05-0001",
                "котельная_наименование": "Котельная №1",
            }
        ],
    }
    CLIENT.post("/hs/boiler/materials", json=payload, headers=AUTH_HEADER)
    data = CLIENT.get("/admin/received/materials").json()
    assert "2026-05" in data


# ── Transactions ──────────────────────────────────────────────────────────────

def test_receive_transactions_returns_ok():
    payload = {
        "период": "2026-04",
        "проводки": [
            {
                "дата": "2026-04-30",
                "дебет_счёт": "20",
                "кредит_счёт": "10",
                "сумма": 25000.0,
                "содержание": "Списание материалов",
                "субконто_дт": "Котельная №5",
                "субконто_кт": "Прокладка резиновая",
            }
        ],
    }
    resp = CLIENT.post("/hs/boiler/transactions", json=payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["проведено_проводок"] == 1


# ── Timesheet ─────────────────────────────────────────────────────────────────

def test_receive_timesheet_returns_ok():
    payload = {
        "период": "2026-04",
        "табель": [
            {
                "сотрудник_id": 7,
                "сотрудник_фио": "Иванов И.И.",
                "обычные_часы": 168,
                "сверхурочные": 0,
                "отпуск": 0,
                "больничный": 0,
            }
        ],
    }
    resp = CLIENT.post("/hs/boiler/timesheet", json=payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["получено_строк"] == 1


# ── Payslips ──────────────────────────────────────────────────────────────────

def test_receive_payslips_returns_ok():
    resp = CLIENT.post(
        "/hs/boiler/payslips",
        json={"период": "2026-04", "запрос": "сформировать_расчётные_листки"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["статус"] == "ok"
    assert body["сформировано"] > 0
    assert len(body["расчётные_листки"]) == body["сформировано"]
    листок = body["расчётные_листки"][0]
    assert "сотрудник_id" in листок
    assert "к_выплате" in листок
    assert "ссылка_pdf" in листок

def test_payslips_use_timesheet_data_when_available():
    """When timesheet was received for period, payslips derive amounts from it."""
    CLIENT.post("/hs/boiler/timesheet", json={
        "период": "2026-04",
        "табель": [
            {"сотрудник_id": 42, "сотрудник_фио": "Тестов Т.Т.", "обычные_часы": 160,
             "сверхурочные": 0, "отпуск": 0, "больничный": 0},
        ],
    }, headers=AUTH_HEADER)

    resp = CLIENT.post(
        "/hs/boiler/payslips",
        json={"период": "2026-04", "запрос": "сформировать_расчётные_листки"},
        headers=AUTH_HEADER,
    )
    листки = resp.json()["расчётные_листки"]
    assert any(л["сотрудник_id"] == 42 for л in листки)


# ── Admin ─────────────────────────────────────────────────────────────────────

def test_admin_stats_empty():
    resp = CLIENT.get("/admin/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["актов"] == 0
    assert stats["проводок"] == 0

def test_admin_stats_after_data():
    CLIENT.post("/hs/boiler/acts", json={
        "период": "2026-04",
        "акты": [
            {
                "номер_акта": "АКТ-0001",
                "дата": "2026-04-01",
                "котельная_id": 1,
                "котельная_наименование": "К1",
                "бригада": "Б1",
                "сумма": 1000.0,
                "материалы": [],
            }
        ],
    }, headers=AUTH_HEADER)
    CLIENT.post("/hs/boiler/transactions", json={
        "период": "2026-04",
        "проводки": [
            {
                "дата": "2026-04-30",
                "дебет_счёт": "62",
                "кредит_счёт": "90.01",
                "сумма": 1000.0,
                "содержание": "Реализация",
            }
        ],
    }, headers=AUTH_HEADER)
    stats = CLIENT.get("/admin/stats").json()
    assert stats["актов"] == 1
    assert stats["проводок"] == 1

def test_admin_clear_resets_all():
    CLIENT.post("/hs/boiler/timesheet", json={
        "период": "2026-04",
        "табель": [{"сотрудник_id": 1, "сотрудник_фио": "Х", "обычные_часы": 160,
                    "сверхурочные": 0, "отпуск": 0, "больничный": 0}],
    }, headers=AUTH_HEADER)
    CLIENT.delete("/admin/received/clear")
    stats = CLIENT.get("/admin/stats").json()
    assert all(v == 0 for v in stats.values())
