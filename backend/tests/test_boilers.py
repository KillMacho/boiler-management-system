"""CRUD tests for /api/v1/boilers/ — create, update, soft-delete, include_deleted."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Тестовая котельная — создаётся и удаляется в рамках теста
NEW_BOILER = {
    "name": "Тест-котельная pytest",
    "address": "ул. Тестовая, 999",
    "latitude": "55.7558",
    "longitude": "37.6173",
    "commissioning_date": "2020-01-01",
    "status": "active",
}


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_list_boilers(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/boilers/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Скрипт 05_InsertTestData.sql добавляет 15 котельных
    assert len(data) >= 15


@pytest.mark.asyncio
async def test_boiler_crud_and_soft_delete(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    # Создаём котельную
    resp = await client.post("/api/v1/boilers/", json=NEW_BOILER, headers=headers)
    assert resp.status_code == 201, resp.text
    boiler = resp.json()
    boiler_id = boiler["id"]
    assert boiler["name"] == NEW_BOILER["name"]
    assert boiler["status"] == "active"

    # Обновляем название
    resp = await client.put(
        f"/api/v1/boilers/{boiler_id}",
        json={"name": "Тест-котельная UPDATED"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Тест-котельная UPDATED"

    # Мягкое удаление — запись остаётся в БД со статусом decommissioned
    resp = await client.delete(f"/api/v1/boilers/{boiler_id}", headers=headers)
    assert resp.status_code == 204

    # Без флага include_deleted удалённая котельная не видна
    resp = await client.get("/api/v1/boilers/", headers=headers)
    ids = [b["id"] for b in resp.json()]
    assert boiler_id not in ids

    # С include_deleted=true — видна, статус decommissioned
    resp = await client.get(
        "/api/v1/boilers/", params={"include_deleted": "true"}, headers=headers
    )
    assert resp.status_code == 200
    found = next((b for b in resp.json() if b["id"] == boiler_id), None)
    assert found is not None, "Soft-deleted boiler must appear with include_deleted=true"
    assert found["status"] == "decommissioned"


@pytest.mark.asyncio
async def test_get_nonexistent_boiler(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/boilers/999999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_boiler_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/boilers/", json=NEW_BOILER)
    assert resp.status_code == 401
