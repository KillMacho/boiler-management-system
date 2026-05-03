"""Tests for mock EDO operator: upload, status progression, auth, admin."""
from __future__ import annotations

import io
import sys
import os
import time

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.storage import storage

CLIENT = TestClient(app)
API_KEY = "demo_api_key_replace_in_production"
HEADERS = {"X-API-Key": API_KEY}
BAD_HEADERS = {"X-API-Key": "wrong_key"}

SAMPLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Файл ИдФайл="TEST" ВерсФорм="5.04">\n'
    '  <Документ КНД="1151100"/>\n'
    '</Файл>'
).encode("utf-8")


@pytest.fixture(autouse=True)
def reset_storage():
    storage.clear()
    yield
    storage.clear()


# ── health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = CLIENT.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── auth ──────────────────────────────────────────────────────────────────────

def test_upload_requires_api_key():
    resp = CLIENT.post(
        "/api/v1/submission/upload",
        files={"file": ("report.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
    )
    assert resp.status_code == 401

def test_upload_rejects_wrong_key():
    resp = CLIENT.post(
        "/api/v1/submission/upload",
        headers=BAD_HEADERS,
        files={"file": ("report.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
    )
    assert resp.status_code == 401

def test_status_requires_api_key():
    resp = CLIENT.get("/api/v1/status/SUB-2026-01-01-00001")
    assert resp.status_code == 401

def test_list_requires_api_key():
    resp = CLIENT.get("/api/v1/submission/list?inn=7700000001&period=2026-Q1")
    assert resp.status_code == 401


# ── upload ────────────────────────────────────────────────────────────────────

def test_upload_returns_submission_id():
    resp = CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("6ndfl.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "submission_id" in body
    assert body["submission_id"].startswith("SUB-")
    assert "receipt_number" in body
    assert body["receipt_number"].startswith("КВТ-")
    assert body["status"] == "accepted"
    assert body["estimated_processing_minutes"] == 15

def test_upload_all_report_types():
    for rtype in ("6-NDFL", "RSV", "4-FSS", "SZV-STAZH"):
        resp = CLIENT.post(
            "/api/v1/submission/upload",
            headers=HEADERS,
            files={"file": (f"{rtype}.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
            data={"report_type": rtype, "period": "2026-Q1", "inn": "7700000001"},
        )
        assert resp.status_code == 200, f"Failed for {rtype}: {resp.text}"
        assert resp.json()["status"] == "accepted"

def test_upload_saves_to_admin():
    CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("test.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "RSV", "period": "2026-Q1", "inn": "7700000001"},
    )
    all_resp = CLIENT.get("/admin/all")
    assert all_resp.status_code == 200
    items = all_resp.json()
    assert len(items) == 1
    assert items[0]["report_type"] == "RSV"
    assert items[0]["inn"] == "7700000001"


# ── status ────────────────────────────────────────────────────────────────────

def test_status_404_for_unknown():
    resp = CLIENT.get("/api/v1/status/NONEXISTENT", headers=HEADERS)
    assert resp.status_code == 404

def test_status_initially_accepted():
    upload = CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("f.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
    )
    sub_id = upload.json()["submission_id"]
    resp = CLIENT.get(f"/api/v1/status/{sub_id}", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["submission_id"] == sub_id
    assert body["status"] == "accepted"
    assert len(body["history"]) >= 1

def test_status_progresses_to_confirmed():
    """Status should reach 'confirmed' after ~15s of monotonic time.
    We inject by manipulating the first_status_check_at timestamp.
    """
    upload = CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("f.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "4-FSS", "period": "2026-Q1", "inn": "7700000001"},
    )
    sub_id = upload.json()["submission_id"]

    # Trigger first check to set first_status_check_at
    CLIENT.get(f"/api/v1/status/{sub_id}", headers=HEADERS)

    # Manually rewind the timer by 20 seconds
    import time
    record = storage._submissions[sub_id]
    record.first_status_check_at = time.monotonic() - 20

    resp = CLIENT.get(f"/api/v1/status/{sub_id}", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["authority_confirmation"] is not None
    assert body["authority_confirmation"]["confirmation_number"].startswith("ФНС-")


# ── list ──────────────────────────────────────────────────────────────────────

def test_list_returns_matching_submissions():
    for _ in range(3):
        CLIENT.post(
            "/api/v1/submission/upload",
            headers=HEADERS,
            files={"file": ("f.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
            data={"report_type": "6-NDFL", "period": "2026-Q1", "inn": "7700000001"},
        )
    # Different inn
    CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("f.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "RSV", "period": "2026-Q1", "inn": "9999999999"},
    )
    resp = CLIENT.get(
        "/api/v1/submission/list?inn=7700000001&period=2026-Q1",
        headers=HEADERS,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert all(i["inn"] == "7700000001" for i in items)


# ── admin ─────────────────────────────────────────────────────────────────────

def test_admin_file_download():
    upload = CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("report.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "SZV-STAZH", "period": "2026", "inn": "7700000001"},
    )
    sub_id = upload.json()["submission_id"]
    resp = CLIENT.get(f"/admin/file/{sub_id}")
    assert resp.status_code == 200
    assert "Файл".encode("utf-8") in resp.content  # XML content present

def test_admin_file_404_for_unknown():
    resp = CLIENT.get("/admin/file/NONEXISTENT")
    assert resp.status_code == 404

def test_admin_clear():
    CLIENT.post(
        "/api/v1/submission/upload",
        headers=HEADERS,
        files={"file": ("f.xml", io.BytesIO(SAMPLE_XML), "application/xml")},
        data={"report_type": "RSV", "period": "2026-Q1", "inn": "7700000001"},
    )
    CLIENT.delete("/admin/clear")
    resp = CLIENT.get("/admin/all")
    assert resp.json() == []
