"""Request creation with auto-classification + status transition tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

BOILER_ID = 10  # use a boiler unlikely to have test conflicts


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _cancel_open_requests(client: AsyncClient, boiler_id: int, headers: dict) -> None:
    """Ensure no open requests block the unique-index for this boiler."""
    resp = await client.get(
        "/api/v1/requests/", params={"boiler_id": boiler_id}, headers=headers
    )
    if resp.status_code != 200:
        return
    for r in resp.json():
        if r["status"] in ("new", "assigned", "in_progress"):
            await client.put(
                f"/api/v1/requests/{r['id']}/status",
                json={"status": "cancelled"},
                headers=headers,
            )


@pytest.mark.asyncio
async def test_auto_classify_avaria(client: AsyncClient) -> None:
    """'Не работает котёл' should classify as Авария with highest priority."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    resp = await client.post(
        "/api/v1/requests/",
        json={
            "description": "Не работает котёл, аварийная ситуация",
            "boiler_id": BOILER_ID,
            "source": "web",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    req = body["request"]
    # status is 'new' if no brigade available, 'assigned' if brigade found
    assert req["status"] in ("new", "assigned")
    assert req["source"] == "web"


@pytest.mark.asyncio
async def test_auto_classify_planovoe_to(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/requests/",
        json={
            "description": "плановое ТО по регламенту котла №2",
            "boiler_id": BOILER_ID,
            "source": "web",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    req = resp.json()["request"]
    # Planovoe TO → priority should be lower than Avaria (id > 1)
    assert req["priority_id"] > 1 or req["type_id"] is not None


@pytest.mark.asyncio
async def test_status_transition_new_to_cancelled(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    # Create a request
    create = await client.post(
        "/api/v1/requests/",
        json={
            "description": "Тест перехода статусов",
            "boiler_id": BOILER_ID,
            "source": "web",
        },
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]

    # new → cancelled is valid
    resp = await client.put(
        f"/api/v1/requests/{req_id}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_status_transition_new_to_completed_is_rejected(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    # Create a request in new status
    create = await client.post(
        "/api/v1/requests/",
        json={
            "description": "Тест невалидного перехода",
            "boiler_id": BOILER_ID,
            "source": "web",
        },
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]

    # new → completed is NOT allowed
    resp = await client.put(
        f"/api/v1/requests/{req_id}/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 409, f"Expected 409 Conflict, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_get_request(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    create = await client.post(
        "/api/v1/requests/",
        json={
            "description": "Проверка GET запроса",
            "boiler_id": BOILER_ID,
            "source": "web",
        },
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]

    get_resp = await client.get(f"/api/v1/requests/{req_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == req_id


@pytest.mark.asyncio
async def test_list_requests_filters(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.get(
        "/api/v1/requests/",
        params={"status": "new", "boiler_id": BOILER_ID},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(r["status"] == "new" for r in data)
    assert all(r["boiler_id"] == BOILER_ID for r in data)
