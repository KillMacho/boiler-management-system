"""Notification stub — logs events to stdout. Real channel TBD (email/SMS)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("notifications")


async def send(event: dict[str, Any]) -> None:
    """Async to keep the call signature future-proof for real transports."""
    logger.info("notification: %s", event)
