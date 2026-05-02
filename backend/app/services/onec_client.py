"""1С integration client — stub implementation.

Real HTTP calls to be implemented in Day 5-6 when mock-server is available.
All methods return {"status": "pending_implementation"}.
Credentials are loaded from settings (ONEC_BASE_URL, ONEC_USERNAME, ONEC_PASSWORD).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("onec_client")

_STUB = {"status": "pending_implementation"}


class OneCClient:
    """Stub 1С integration client. Methods log intent and return pending stub."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self._base_url = base_url
        self._username = username
        logger.info("OneCClient initialized (stub) base_url=%s", base_url)

    async def send_acts(self, period_data: Any) -> dict:
        logger.info("send_acts called (stub) data=%s", period_data)
        return _STUB

    async def send_materials(self, period_data: Any) -> dict:
        logger.info("send_materials called (stub) data=%s", period_data)
        return _STUB

    async def send_transactions(self, transactions: Any) -> dict:
        logger.info("send_transactions called (stub) data=%s", transactions)
        return _STUB

    async def send_timesheet(self, period_data: Any) -> dict:
        logger.info("send_timesheet called (stub) data=%s", period_data)
        return _STUB

    async def send_payslip_request(self, employee_id: int, period: str) -> dict:
        logger.info("send_payslip_request employee_id=%s period=%s (stub)", employee_id, period)
        return _STUB


def _make_client() -> OneCClient:
    try:
        from app.config import settings  # late import for test isolation
        base_url = getattr(settings, "onec_base_url", "http://localhost:8080")
        username = getattr(settings, "onec_username", "admin")
        password = getattr(settings, "onec_password", "")
    except Exception:
        base_url, username, password = "http://localhost:8080", "admin", ""
    return OneCClient(base_url=base_url, username=username, password=password)


onec_client: OneCClient = _make_client()
