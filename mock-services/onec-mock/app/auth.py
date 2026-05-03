"""HTTP Basic Auth dependency — mirrors 1C HTTP-service authentication."""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import settings

security = HTTPBasic()


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Validate Basic Auth credentials against settings.

    Uses constant-time comparison to prevent timing attacks.
    Returns the authenticated username.
    """
    correct_username = secrets.compare_digest(
        credentials.username.encode(), settings.onec_mock_username.encode()
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode(), settings.onec_mock_password.encode()
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
