"""API Key authentication — mirrors Kontur.Extern / SBIS EDO operator auth model."""
from __future__ import annotations

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """Validate X-API-Key header against settings.

    Returns the key on success, raises 401 otherwise.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует заголовок X-API-Key",
        )
    if not secrets.compare_digest(api_key.encode(), settings.edo_mock_api_key.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный API-ключ",
        )
    return api_key
