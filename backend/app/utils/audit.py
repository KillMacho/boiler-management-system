"""@audit_action decorator for automatic audit logging on service functions.

Usage:
    @audit_action("request_created", "request")
    async def create_request(session, payload, *, user_id, ...):
        ...
        return request_obj  # must have .id attribute

The decorator:
  - Calls the wrapped function.
  - Extracts session from kwargs or positional arg[0].
  - Extracts user_id from kwargs.
  - Gets entity_id from result.id (if available).
  - Calls audit_service.log(autocommit=True).
"""
from __future__ import annotations

import functools
import logging
from typing import Callable

logger = logging.getLogger("audit_decorator")


def audit_action(action: str, entity_type: str):
    """Decorator that logs an audit entry after the decorated async function returns."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Resolve session: first kwarg named 'session', or positional arg[0]
            session = kwargs.get("session") or (args[0] if args else None)
            user_id = kwargs.get("user_id")
            entity_id = getattr(result, "id", None)

            if session is not None:
                try:
                    from app.services import audit_service  # avoid circular at import time

                    await audit_service.log(
                        session,
                        user_id=user_id,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        autocommit=True,
                    )
                except Exception:
                    logger.warning(
                        "audit_action failed for %s/%s entity_id=%s",
                        action,
                        entity_type,
                        entity_id,
                        exc_info=True,
                    )

            return result

        return wrapper

    return decorator
