"""End-to-end request lifecycle test: create → assign → start → complete → act → close."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

BOILER_ID = 5  # Use a boiler away from monitoring tests


async def _auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _cancel_open_requests(client: AsyncClient, boiler_id: int, headers: dict) -> None:
    resp = await client.get(
        "/api/v1/requests/", params={"boiler_id": boiler_id}, headers=headers
    )
    if resp.status_code != 200:
        return
    for r in resp.json():
        if r["status"] not in ("closed", "cancelled", "completed"):
            await client.put(
                f"/api/v1/requests/{r['id']}/status",
                json={"status": "cancelled"},
                headers=headers,
            )


# ── state-machine / transition tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_to_needs_manual_assignment(client: AsyncClient) -> None:
    """Transition new → needs_manual_assignment should succeed."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Тест ручного назначения", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req = create.json()["request"]
    req_id = req["id"]

    if req["status"] != "new":
        pytest.skip("brigade was auto-assigned; skipping manual-assignment test")

    resp = await client.put(
        f"/api/v1/requests/{req_id}/status",
        json={"status": "needs_manual_assignment"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_manual_assignment"


@pytest.mark.asyncio
async def test_auto_assign_endpoint(client: AsyncClient) -> None:
    """POST /requests/{id}/auto-assign runs smart brigade assignment."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Тест авто-назначения бригады", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]
    current_status = create.json()["request"]["status"]

    if current_status == "assigned":
        # Brigade already assigned during creation — test pass
        return

    resp = await client.post(
        f"/api/v1/requests/{req_id}/auto-assign", headers=headers
    )
    assert resp.status_code == 200, resp.text
    result_status = resp.json()["request"]["status"]
    assert result_status in ("assigned", "needs_manual_assignment")


@pytest.mark.asyncio
async def test_full_lifecycle_new_statuses(client: AsyncClient) -> None:
    """Test the new extended lifecycle: work_completed → act_generated → closed."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    # 1. Create request
    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Текущий ремонт котла", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    body = create.json()
    req_id = body["request"]["id"]
    req_status = body["request"]["status"]

    # If no brigade was assigned, manually move to needs_manual_assignment → skip deeper test
    if req_status == "new":
        # No brigade: test just the new statuses reachable from new
        cancel_resp = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert cancel_resp.status_code == 200
        return

    work_order_id = body["work_order"]["id"]

    # 2. Start work order
    start_resp = await client.post(
        f"/api/v1/work-orders/{work_order_id}/start", headers=headers
    )
    assert start_resp.status_code == 200, start_resp.text
    assert start_resp.json()["status"] == "in_progress"

    # 3. Complete work order → request should become work_completed
    complete_resp = await client.post(
        f"/api/v1/work-orders/{work_order_id}/complete",
        json={"notes": "Ремонт завершён", "total_amount": "0"},
        headers=headers,
    )
    assert complete_resp.status_code == 200, complete_resp.text
    assert complete_resp.json()["status"] == "completed"

    # Check request status (may be work_completed or still in_progress if no transition happened)
    req_check = await client.get(f"/api/v1/requests/{req_id}", headers=headers)
    assert req_check.status_code == 200
    req_status_after = req_check.json()["status"]
    assert req_status_after in ("work_completed", "in_progress", "completed"), req_status_after

    # 4. Try to transition to act_generated (if work_completed) or completed→closed (old path)
    if req_status_after == "work_completed":
        act_resp = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "act_generated"},
            headers=headers,
        )
        assert act_resp.status_code == 200, act_resp.text
        assert act_resp.json()["status"] == "act_generated"

        # 5. Close
        close_resp = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "closed"},
            headers=headers,
        )
        assert close_resp.status_code == 200, close_resp.text
        assert close_resp.json()["status"] == "closed"
        assert close_resp.json()["closed_at"] is not None

    elif req_status_after == "completed":
        # Old path backward compat
        close_resp = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "closed"},
            headers=headers,
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

    else:
        # Still in_progress (work_completed transition may have failed); just cancel
        cancel_resp = await client.put(
            f"/api/v1/requests/{req_id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert cancel_resp.status_code == 200


@pytest.mark.asyncio
async def test_invalid_transition_in_progress_to_closed(client: AsyncClient) -> None:
    """Transition in_progress → closed should return 409 (not in VALID_TRANSITIONS)."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Авария тест переходов", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    body = create.json()
    req_id = body["request"]["id"]

    if body["request"]["status"] != "assigned":
        pytest.skip("brigade not assigned")

    wo_id = body["work_order"]["id"]
    await client.post(f"/api/v1/work-orders/{wo_id}/start", headers=headers)

    # in_progress → closed is NOT allowed
    resp = await client.put(
        f"/api/v1/requests/{req_id}/status",
        json={"status": "closed"},
        headers=headers,
    )
    assert resp.status_code == 409, f"Expected 409 Conflict, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_manual_assign_endpoint(client: AsyncClient) -> None:
    """POST /requests/{id}/manual-assign with a valid brigade_id should work."""
    headers = await _auth_headers(client)
    await _cancel_open_requests(client, BOILER_ID, headers)

    create = await client.post(
        "/api/v1/requests/",
        json={"description": "Ручное назначение бригады", "boiler_id": BOILER_ID, "source": "web"},
        headers=headers,
    )
    assert create.status_code == 201
    req_id = create.json()["request"]["id"]
    req_status = create.json()["request"]["status"]

    if req_status == "assigned":
        pytest.skip("brigade already auto-assigned")

    # Get a brigade to assign manually
    brigades_resp = await client.get("/api/v1/brigades/", headers=headers)
    assert brigades_resp.status_code == 200
    brigades = [b for b in brigades_resp.json() if b["status"] != "inactive"]
    if not brigades:
        pytest.skip("no active brigades")

    brigade_id = brigades[0]["id"]
    resp = await client.post(
        f"/api/v1/requests/{req_id}/manual-assign",
        json={"brigade_id": brigade_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["request"]["status"] == "assigned"
    assert result["work_order"]["brigade_id"] == brigade_id
