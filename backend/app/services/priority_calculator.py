"""Priority calculation with source and boiler-type awareness.

Rules (in order of precedence):
  1. source in ('monitoring', 'ml_prediction')  → Критический
  2. type_name == 'Авария'                       → Критический
  3. boiler name contains 'критическ' and
     base priority is not already Критический   → elevate to Высокий
  4. Otherwise: priority from _TYPE_PRIORITY_MAP
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("priority_calculator")

_TYPE_PRIORITY_MAP: dict[str, str] = {
    "Авария": "Критический",
    "Аварийное ТО": "Высокий",
    "Плановое ТО": "Средний",
    "Текущий ремонт": "Средний",
    "Предиктивное ТО": "Средний",
}

_LEVELS = ["Низкий", "Средний", "Высокий", "Критический"]


def _elevate(priority_name: str) -> str:
    """Raise priority one level (capped at Критический)."""
    idx = _LEVELS.index(priority_name) if priority_name in _LEVELS else 1
    return _LEVELS[min(idx + 1, len(_LEVELS) - 1)]


async def compute_priority_name(
    session: AsyncSession,
    *,
    type_name: str,
    source: str,
    boiler_id: int,
    reference_cache,
) -> str:
    """Return the priority name (e.g. 'Критический') for the given context."""
    # Rule 1: auto-sources always critical
    if source in ("monitoring", "ml_prediction"):
        return "Критический"

    # Rule 2: base priority by type
    base = _TYPE_PRIORITY_MAP.get(type_name, "Средний")

    # Rule 3: critical boiler name → boost
    if base != "Критический":
        try:
            from app.models.boilers import Boiler  # late import avoids circular

            boiler = await session.get(Boiler, boiler_id)
            if boiler and "критическ" in boiler.name.lower():
                base = _elevate(base)
                logger.debug(
                    "boosted priority to %s for boiler_id=%s ('%s')",
                    base,
                    boiler_id,
                    boiler.name,
                )
        except Exception:
            logger.warning("could not load boiler_id=%s for priority boost", boiler_id)

    return base
