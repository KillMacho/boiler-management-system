"""JSON encoder safe for SQL-Server-style values (Decimal/datetime/date).

Used to serialise audit_log.details: SQL Server CHECK constraint requires
ISJSON(details) = 1, and json.dumps cannot encode Decimal/datetime by default.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)  # str — точность не теряется (в отличие от float)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def safe_json_dumps(obj: Any) -> str:
    """Serialise obj to a JSON string accepted by SQL Server's ISJSON()."""
    return json.dumps(obj, default=_default, ensure_ascii=False)
