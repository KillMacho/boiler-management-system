"""Threshold evaluation + boiler status cache + auto-request escalation."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import Threshold
from app.services import audit_service, request_service

logger = logging.getLogger("monitoring_service")

# Полный список параметров, которые проверяются на превышение порогов
PARAMETER_NAMES = (
    "temperature_heat",
    "pressure",
    "co_level",
    "gas_flow",
    "water_level",
    "temperature_return",
    "furnace_draft",
)

# Числовой ранг тяжести нужен, чтобы взять максимум из множества нарушений
_SEVERITY_ORDER = {"normal": 0, "warning": 1, "critical": 2}
_TELEMETRY_STATUS = {0: "normal", 1: "warning", 2: "critical"}
_DASHBOARD_STATUS = {0: "green", 1: "yellow", 2: "red"}


@dataclass
class Breach:
    parameter: str
    value: Optional[Decimal]
    kind: str  # "warning" | "critical"
    bound: str  # "min_warning" | "max_warning" | "min_critical" | "max_critical"
    threshold_value: Optional[Decimal]


@dataclass
class EvalResult:
    overall: str  # "normal" | "warning" | "critical"
    dashboard_status: str  # "green" | "yellow" | "red"
    breaches: List[Breach] = field(default_factory=list)


def _check_param(
    value: Optional[Decimal], threshold: Threshold
) -> Optional[Breach]:
    """Return the most severe breach for a single parameter, if any."""
    if value is None:
        return None
    # critical wins over warning
    if threshold.min_critical is not None and value < threshold.min_critical:
        return Breach(threshold.parameter_name, value, "critical", "min_critical", threshold.min_critical)
    if threshold.max_critical is not None and value > threshold.max_critical:
        return Breach(threshold.parameter_name, value, "critical", "max_critical", threshold.max_critical)
    if threshold.min_warning is not None and value < threshold.min_warning:
        return Breach(threshold.parameter_name, value, "warning", "min_warning", threshold.min_warning)
    if threshold.max_warning is not None and value > threshold.max_warning:
        return Breach(threshold.parameter_name, value, "warning", "max_warning", threshold.max_warning)
    return None


async def _load_thresholds(
    session: AsyncSession, boiler_id: int
) -> Dict[str, Threshold]:
    """boiler-specific takes precedence; fallback to NULL (общий)."""
    stmt = select(Threshold).where(
        (Threshold.boiler_id == boiler_id) | (Threshold.boiler_id.is_(None))
    )
    rows = (await session.execute(stmt)).scalars().all()
    out: Dict[str, Threshold] = {}
    for row in rows:
        # Загружаем пороги: специфичные для котельной перекрывают общие
        existing = out.get(row.parameter_name)
        if existing is None or (existing.boiler_id is None and row.boiler_id is not None):
            out[row.parameter_name] = row
    return out


async def evaluate(
    session: AsyncSession,
    *,
    boiler_id: int,
    parameters: Dict[str, Optional[Decimal]],
    auto_create_request: bool = True,
) -> EvalResult:
    thresholds = await _load_thresholds(session, boiler_id)
    breaches: List[Breach] = []
    for name in PARAMETER_NAMES:
        threshold = thresholds.get(name)
        if threshold is None:
            continue
        breach = _check_param(parameters.get(name), threshold)
        if breach is not None:
            breaches.append(breach)

    severity = max((_SEVERITY_ORDER[b.kind] for b in breaches), default=0)
    overall = _TELEMETRY_STATUS[severity]
    dashboard = _DASHBOARD_STATUS[severity]
    result = EvalResult(overall=overall, dashboard_status=dashboard, breaches=breaches)

    # Сохраняем снимок в кеш при любом статусе — дашборд опрашивает только кеш
    StatusCache.put(
        boiler_id,
        {
            "status": dashboard,
            "telemetry_status": overall,
            "parameters": {k: (str(v) if v is not None else None) for k, v in parameters.items()},
            "breaches": [
                {"parameter": b.parameter, "kind": b.kind, "value": str(b.value)}
                for b in breaches
            ],
            "updated_at": time.time(),
        },
    )

    # При критическом нарушении автоматически создаём аварийную заявку (дедупликация внутри)
    if auto_create_request and overall == "critical":
        critical_breach = next((b for b in breaches if b.kind == "critical"), None)
        if critical_breach is not None:
            try:
                created = await request_service.create_auto_request(
                    session,
                    boiler_id=boiler_id,
                    parameter_name=critical_breach.parameter,
                    value=str(critical_breach.value),
                    threshold_kind=critical_breach.bound,
                )
                if created is not None:
                    await audit_service.log(
                        session,
                        user_id=None,
                        action="threshold_breached",
                        entity_type="boiler",
                        entity_id=boiler_id,
                        details={
                            "parameter": critical_breach.parameter,
                            "value": str(critical_breach.value),
                            "kind": critical_breach.bound,
                            "auto_request_id": created.id,
                        },
                        autocommit=True,
                    )
            except Exception:  # noqa: BLE001 — telemetry must not fail on monitor errors
                logger.exception("auto-request creation failed for boiler_id=%s", boiler_id)

    return result


class StatusCache:
    """In-memory snapshot of latest dashboard status per boiler.

    Single-writer (telemetry POST) / multi-reader (dashboard) — atomic dict
    swap is enough; no locks. Multi-worker uvicorn would split the cache;
    documented as TODO Day 5 (Redis).
    """

    _store: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def put(cls, boiler_id: int, snapshot: Dict[str, Any]) -> None:
        # Атомарная замена словаря — безопасно для asyncio (нет GIL-опасных рейсов)
        cls._store = {**cls._store, boiler_id: snapshot}

    @classmethod
    def get(cls, boiler_id: int) -> Optional[Dict[str, Any]]:
        return cls._store.get(boiler_id)

    @classmethod
    def all(cls) -> Dict[int, Dict[str, Any]]:
        return dict(cls._store)

    @classmethod
    def clear(cls) -> None:
        cls._store = {}
