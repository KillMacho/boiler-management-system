"""In-memory storage — emulates 1C database that accumulates received documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ReceivedRecord:
    received_at: str
    data: Any


class OneCMockStorage:
    """Thread-safe (single-worker) in-memory store keyed by document type."""

    def __init__(self) -> None:
        self.acts: dict[str, list[ReceivedRecord]] = {}
        self.materials: dict[str, list[ReceivedRecord]] = {}
        self.transactions: dict[str, list[ReceivedRecord]] = {}
        self.timesheet: dict[str, list[ReceivedRecord]] = {}
        self.payslips: dict[str, list[ReceivedRecord]] = {}

    # ── acts ─────────────────────────────────────────────────────────────────

    def add_acts(self, period: str, data: Any) -> None:
        self.acts.setdefault(period, []).append(
            ReceivedRecord(received_at=_now(), data=data)
        )

    def get_acts(self) -> dict:
        return _serialize(self.acts)

    # ── materials ─────────────────────────────────────────────────────────────

    def add_materials(self, period: str, data: Any) -> None:
        self.materials.setdefault(period, []).append(
            ReceivedRecord(received_at=_now(), data=data)
        )

    def get_materials(self) -> dict:
        return _serialize(self.materials)

    # ── transactions ──────────────────────────────────────────────────────────

    def add_transactions(self, period: str, data: Any) -> None:
        self.transactions.setdefault(period, []).append(
            ReceivedRecord(received_at=_now(), data=data)
        )

    def get_transactions(self) -> dict:
        return _serialize(self.transactions)

    # ── timesheet ─────────────────────────────────────────────────────────────

    def add_timesheet(self, period: str, data: Any) -> None:
        self.timesheet.setdefault(period, []).append(
            ReceivedRecord(received_at=_now(), data=data)
        )

    def get_timesheet(self) -> dict:
        return _serialize(self.timesheet)

    # ── payslips ──────────────────────────────────────────────────────────────

    def add_payslips(self, period: str, data: Any) -> None:
        self.payslips.setdefault(period, []).append(
            ReceivedRecord(received_at=_now(), data=data)
        )

    def get_payslips(self) -> dict:
        return _serialize(self.payslips)

    # ── admin ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "актов": sum(len(v) for v in self.acts.values()),
            "движений_материалов": sum(len(v) for v in self.materials.values()),
            "проводок": sum(len(v) for v in self.transactions.values()),
            "табель_строк": sum(len(v) for v in self.timesheet.values()),
            "расчётных_листков": sum(len(v) for v in self.payslips.values()),
        }

    def clear(self) -> None:
        self.acts.clear()
        self.materials.clear()
        self.transactions.clear()
        self.timesheet.clear()
        self.payslips.clear()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _serialize(store: dict[str, list[ReceivedRecord]]) -> dict:
    return {
        period: [{"received_at": r.received_at, "data": r.data} for r in records]
        for period, records in store.items()
    }


# Global singleton
storage = OneCMockStorage()
