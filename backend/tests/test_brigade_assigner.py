"""Brigade assigner tests: free brigade list, qualification endpoints, auto/manual assign."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

BOILER_ID = 7  # dedicated boiler for assigner tests


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _cancel_open(client: AsyncClient, boiler_id: int, headers: dict) -> None:
    resp = await client.get(
        "/api/v1/requests/", params={"boiler_id": boiler_id}, headers=headers
    )
    if resp.status_code != 200:
        return
    for r in resp.json():
        if r["status"] not in ("closed", "cancelled", "completed", "act_generated"):
            await client.put(
                f"/api/v1/requests/{r['id']}/status",
                json={"status": "cancelled"},
                headers=headers,
            )


@pytest.mark.asyncio
async def test_free_brigades_returns_list(client: AsyncClient) -> None:
    """GET /brigades/free returns a JSON array (may be empty if all busy)."""
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/brigades/free", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Every returned brigade must not be inactive
    for b in data:
        assert b["status"] != "inactive"


@pytest.mark.asyncio
async def test_brigade_qualifications_for_existing_brigade(client: AsyncClient) -> None:
    """GET /brigades/{id}/qualifications returns qualification summaries."""
    headers = await _auth_headers(client)
    brigades_resp = await client.get("/api/v1/brigades/", headers=headers)
    assert brigades_resp.status_code == 200
    brigades = [b for b in brigades_resp.json() if b["status"] != "inactive"]
    if not brigades:
        pytest.skip("no active brigades in DB")

    brigade_id = brigades[0]["id"]
    resp = await client.get(
        f"/api/v1/brigades/{brigade_id}/qualifications", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for item in data:
        assert "qualification_id" in item
        assert "qualification_name" in item
        assert "employee_count" in item
        assert item["employee_count"] >= 1


@pytest.mark.asyncio
async def test_brigade_qualifications_404_for_nonexistent(client: AsyncClient) -> None:
    """GET /brigades/99999999/qualifications → 404."""
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/brigades/99999999/qualifications", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_auto_assign_on_new_request(client: AsyncClient) -> None:
    """POST /requests/{id}/auto-assign on a 'new' request triggers smart assignment."""
    headers = await _auth_headers(client)
    await _cancel_open(client, BOILER_ID, headers)

    # Create request; if brigade was auto-assigned during creation, that's also fine
    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Тест авто-назначения", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]
    initial_status = create.json()["request"]["status"]

    if initial_status != "new":
        # Brigade was already assigned — cancel and recreate isn't needed;
        # test the endpoint on needs_manual_assignment path
        mv = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert mv.status_code == 200
        pytest.skip("brigade was auto-assigned during creation; skip redundant auto-assign test")

    resp = await client.post(f"/api/v1/requests/{req_id}/auto-assign", headers=headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["request"]["status"] in ("assigned", "needs_manual_assignment")
    if result["request"]["status"] == "assigned":
        assert result["work_order"] is not None
        assert result["work_order"]["brigade_id"] > 0


@pytest.mark.asyncio
async def test_auto_assign_rejects_already_assigned(client: AsyncClient) -> None:
    """POST /requests/{id}/auto-assign on 'assigned' request → 409."""
    headers = await _auth_headers(client)
    await _cancel_open(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Тест двойного назначения", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]

    if create.json()["request"]["status"] != "assigned":
        pytest.skip("no brigade was assigned; can't test double-assign rejection")

    resp = await client.post(f"/api/v1/requests/{req_id}/auto-assign", headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_manual_assign_with_specific_brigade(client: AsyncClient) -> None:
    """POST /requests/{id}/manual-assign assigns the specified brigade."""
    headers = await _auth_headers(client)
    await _cancel_open(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Ручная бригада", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]

    if create.json()["request"]["status"] == "assigned":
        # Cancel the auto-assigned work; won't work since we can't "unassign"
        # Just skip: already assigned during creation
        pytest.skip("brigade auto-assigned; manual-assign test skipped")

    brigades = await client.get("/api/v1/brigades/", headers=headers)
    active = [b for b in brigades.json() if b["status"] != "inactive"]
    if not active:
        pytest.skip("no active brigades in DB")

    brigade_id = active[0]["id"]
    resp = await client.post(
        f"/api/v1/requests/{req_id}/manual-assign",
        json={"brigade_id": brigade_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["request"]["status"] == "assigned"
    assert result["work_order"]["brigade_id"] == brigade_id
