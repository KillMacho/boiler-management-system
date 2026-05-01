"""FastAPI dependencies: get_current_user, RoleChecker."""
from __future__ import annotations

from typing import Iterable, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.services import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = auth_service.decode_token(token)
    except auth_service.JWTError:
        raise CREDENTIALS_EXC

    if payload.type != "access":
        raise CREDENTIALS_EXC

    if auth_service.is_blacklisted(payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload.sub)
    except (TypeError, ValueError):
        raise CREDENTIALS_EXC

    user = await auth_service.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_EXC
    return user


class RoleChecker:
    """Dependency that allows access only to users with at least one of the
    required roles. Use in routes:

        @router.get("/x", dependencies=[Depends(RoleChecker(["chief_engineer"]))])
    """

    def __init__(self, allowed_roles: Iterable[str]) -> None:
        self.allowed_roles: List[str] = list(allowed_roles)

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_roles = set(user.role_names)
        if not user_roles.intersection(self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {self.allowed_roles}",
            )
        return user
