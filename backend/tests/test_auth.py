"""Smoke tests for /api/auth/* against the real BoilerManagementDB.

The admin user must already exist (run database/06_CreateAdminUser.sql first).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# Учётные данные тестового администратора (создаются скриптом 06_CreateAdminUser.sql)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    # Проверяем, что сервер вообще отвечает
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    # Успешный логин должен вернуть три токена и данные пользователя
    response = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["username"] == ADMIN_USERNAME
    assert "chief_engineer" in body["user"]["roles"] or len(body["user"]["roles"]) >= 1


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    # Неверный пароль → 401
    response = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": "wrong-pass"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client: AsyncClient) -> None:
    # Запрос без токена должен отклоняться
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient) -> None:
    # После логина /me должен вернуть данные текущего пользователя
    login = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["username"] == ADMIN_USERNAME


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    # Refresh-токен должен выдать новый access-токен
    login = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_logout_revokes_token(client: AsyncClient) -> None:
    # После logout токен попадает в blacklist и перестаёт работать
    login = await client.post(
        "/api/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = login.json()["access_token"]

    logout = await client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert logout.status_code == 200

    # Тот же токен после logout должен возвращать 401
    me_after = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_after.status_code == 401
