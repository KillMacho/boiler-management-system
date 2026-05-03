"""EDO operator client — submits XML reports via multipart POST with X-API-Key auth.

Mirrors the API of Kontur.Extern / SBIS: X-API-Key in header,
multipart/form-data with file + metadata fields.
Uses httpx + tenacity (3 retries).
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("edo_client")

_RETRY_ON = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


def _retry():
    return retry(
        retry=retry_if_exception_type(_RETRY_ON),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )


class EDOClient:
    """Async client for EDO operator HTTP API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        logger.info("EDOClient initialized base_url=%s", base_url)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-API-Key": self._api_key},
            timeout=httpx.Timeout(self._timeout),
        )

    @_retry()
    async def submit_report(
        self,
        filepath: str,
        report_type: str,
        period: str,
        inn: str,
    ) -> dict:
        """Upload XML report file via multipart POST.

        Args:
            filepath: Absolute or relative path to the XML file.
            report_type: One of '6-NDFL', 'RSV', '4-FSS', 'SZV-STAZH'.
            period: Reporting period string (e.g. '2026-Q1' or '2026').
            inn: Organization INN (10 digits).

        Returns:
            dict with submission_id, receipt_number, status, etc.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Report file not found: {filepath}")

        file_content = path.read_bytes()
        async with self._client() as client:
            resp = await client.post(
                "/api/v1/submission/upload",
                data={
                    "report_type": report_type,
                    "period": period,
                    "inn": inn,
                },
                files={
                    "file": (path.name, file_content, "application/xml"),
                },
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "submit_report ok: type=%s period=%s sub_id=%s receipt=%s",
                report_type, period,
                result.get("submission_id"),
                result.get("receipt_number"),
            )
            return result

    @_retry()
    async def check_status(self, submission_id: str) -> dict:
        """Check document flow status for a submission."""
        async with self._client() as client:
            resp = await client.get(f"/api/v1/status/{submission_id}")
            resp.raise_for_status()
            return resp.json()

    @_retry()
    async def list_submissions(self, inn: str, period: str) -> list[dict]:
        """List all submissions for a given INN and period."""
        async with self._client() as client:
            resp = await client.get(
                "/api/v1/submission/list",
                params={"inn": inn, "period": period},
            )
            resp.raise_for_status()
            return resp.json()


def _make_client() -> EDOClient:
    try:
        from app.config import settings
        return EDOClient(
            base_url=settings.edo_base_url,
            api_key=settings.edo_api_key,
            timeout=settings.edo_timeout,
        )
    except Exception:
        return EDOClient(
            base_url="http://localhost:8081",
            api_key="demo_api_key_replace_in_production",
        )


edo_client: EDOClient = _make_client()
