"""audit_log writer. Serialises details into JSON acceptable by SQL Server ISJSON()."""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import AuditLog
from app.utils.json_encoder import safe_json_dumps

logger = logging.getLogger("audit")


async def log(
    session: AsyncSession,
    *,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[Any] = None,
    details: Optional[dict] = None,
    autocommit: bool = False,
) -> None:
    """Persist an audit entry. Caller controls transaction unless autocommit=True."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=safe_json_dumps(details) if details is not None else None,
    )
    session.add(entry)
    if autocommit:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("audit log commit failed for action=%s", action)
            raise
