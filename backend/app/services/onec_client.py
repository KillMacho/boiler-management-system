"""1С integration client — sends data to /hs/boiler/* HTTP-services via Basic Auth.

Uses httpx.AsyncClient with tenacity retry (3 attempts, exponential backoff).
All payload keys are in Russian (Cyrillic) to match 1C XDTO format.
"""
from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("onec_client")

_RETRY_ON = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


def _retry_decorator():
    return retry(
        retry=retry_if_exception_type(_RETRY_ON),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )


class OneCClient:
    """Async HTTP client for 1C HTTP-services.

    Each method formats the payload with Cyrillic field names (matching 1C XDTO)
    and POSTs to the corresponding /hs/boiler/* endpoint with Basic Auth.
    """

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (username, password)
        self._timeout = timeout
        logger.info("OneCClient initialized base_url=%s user=%s", base_url, username)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=httpx.Timeout(self._timeout),
        )

    @_retry_decorator()
    async def send_acts(self, period: str, acts: list[dict]) -> dict:
        """Send work acts to 1C.

        Args:
            period: "YYYY-MM" billing period string.
            acts: list of act dicts with keys: номер_акта, дата, котельная_id,
                  котельная_наименование, бригада, сумма, материалы.
        """
        payload = {"период": period, "акты": acts}
        async with self._client() as client:
            resp = await client.post("/hs/boiler/acts", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "send_acts ok: period=%s sent=%d 1c_docs=%s",
                period,
                len(acts),
                result.get("номера_документов_1с", []),
            )
            return result

    @_retry_decorator()
    async def send_materials(self, period: str, movements: list[dict]) -> dict:
        """Send material movements (write-offs, receipts) to 1C.

        Args:
            period: "YYYY-MM" billing period.
            movements: list of movement dicts with keys: тип_операции, дата,
                       номенклатура, количество, сумма, наряд_номер,
                       котельная_наименование.
        """
        payload = {"период": period, "движения_материалов": movements}
        async with self._client() as client:
            resp = await client.post("/hs/boiler/materials", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "send_materials ok: period=%s sent=%d",
                period,
                len(movements),
            )
            return result

    @_retry_decorator()
    async def send_transactions(self, period: str, transactions: list[dict]) -> dict:
        """Send accounting entries (journal transactions) to 1C.

        Args:
            period: "YYYY-MM" billing period.
            transactions: list of dicts with keys: дата, дебет_счёт, кредит_счёт,
                          сумма, содержание, субконто_дт (opt), субконто_кт (opt).
        """
        payload = {"период": period, "проводки": transactions}
        async with self._client() as client:
            resp = await client.post("/hs/boiler/transactions", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "send_transactions ok: period=%s sent=%d",
                period,
                len(transactions),
            )
            return result

    @_retry_decorator()
    async def send_timesheet(self, period: str, rows: list[dict]) -> dict:
        """Send employee timesheet to 1C.

        Args:
            period: "YYYY-MM" billing period.
            rows: list of dicts with keys: сотрудник_id, сотрудник_фио,
                  обычные_часы, сверхурочные, отпуск, больничный.
        """
        payload = {"период": period, "табель": rows}
        async with self._client() as client:
            resp = await client.post("/hs/boiler/timesheet", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "send_timesheet ok: period=%s rows=%d",
                period,
                len(rows),
            )
            return result

    @_retry_decorator()
    async def send_payslip_request(self, period: str) -> dict:
        """Request 1C to generate payslips for the given period.

        Args:
            period: "YYYY-MM" billing period.
        """
        payload = {"период": period, "запрос": "сформировать_расчётные_листки"}
        async with self._client() as client:
            resp = await client.post("/hs/boiler/payslips", json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "send_payslip_request ok: period=%s generated=%d",
                period,
                result.get("сформировано", 0),
            )
            return result


def _make_client() -> OneCClient:
    try:
        from app.config import settings
        return OneCClient(
            base_url=settings.onec_base_url,
            username=settings.onec_username,
            password=settings.onec_password,
            timeout=settings.onec_timeout,
        )
    except Exception:
        return OneCClient(
            base_url="http://localhost:8080",
            username="app_user",
            password="password123",
        )


onec_client: OneCClient = _make_client()
