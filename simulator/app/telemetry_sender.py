"""TelemetrySender: authenticates with the backend and sends readings via httpx + tenacity."""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .boiler_simulator import TelemetryReading
from .config import settings

logger = logging.getLogger("simulator.sender")

_RETRY_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


class TelemetrySender:
    """Manages an httpx.AsyncClient with a JWT token, refreshing it on 401."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def __aenter__(self) -> "TelemetrySender":
        self._client = httpx.AsyncClient(
            base_url=settings.backend_url,
            timeout=httpx.Timeout(5.0),
        )
        await self._authenticate()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _authenticate(self) -> None:
        assert self._client is not None
        resp = await self._client.post(
            "/api/auth/login",
            data={
                "username": settings.admin_username,
                "password": settings.admin_password,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        logger.info("authenticated as '%s'", settings.admin_username)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    @retry(
        retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def send(self, reading: TelemetryReading) -> dict:
        """Send one telemetry reading. Retries on network errors (up to 3 attempts)."""
        assert self._client is not None
        payload = reading.to_dict()
        resp = await self._client.post(
            "/api/v1/telemetry/",
            json=payload,
            headers=self._headers(),
        )
        if resp.status_code == 401:
            # Token expired — re-authenticate and retry once
            await self._authenticate()
            resp = await self._client.post(
                "/api/v1/telemetry/",
                json=payload,
                headers=self._headers(),
            )
        resp.raise_for_status()
        return resp.json()

    async def send_batch(self, readings: list[TelemetryReading]) -> list[dict]:
        """Send a batch via POST /api/v1/telemetry/batch if available, fallback to one-by-one."""
        assert self._client is not None
        payload = [r.to_dict() for r in readings]
        resp = await self._client.post(
            "/api/v1/telemetry/batch",
            json=payload,
            headers=self._headers(),
        )
        if resp.status_code in (404, 405):
            # Endpoint not available — fall back to individual sends
            results = []
            for reading in readings:
                results.append(await self.send(reading))
            return results
        if resp.status_code == 401:
            await self._authenticate()
            resp = await self._client.post(
                "/api/v1/telemetry/batch",
                json=payload,
                headers=self._headers(),
            )
        resp.raise_for_status()
        return resp.json()
