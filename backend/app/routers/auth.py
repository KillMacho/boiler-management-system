"""/api/auth/* — login, refresh, logout, me."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, oauth2_scheme
from app.models.users import User
from app.schemas.auth import (
    AccessTokenOnly,
    RefreshRequest,
    TokenPair,
    UserInfo,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        employee_id=user.employee_id,
        is_active=user.is_active,
        last_login=user.last_login,
        roles=user.role_names,
    )


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Логин по username/password (OAuth2 form-data)",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenPair:
    user = await auth_service.authenticate_user(session, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = user.role_names
    access_token, access_expires = auth_service.create_access_token(
        user.id, user.username, roles
    )
    refresh_token, _ = auth_service.create_refresh_token(
        user.id, user.username, roles
    )

    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    await session.refresh(user)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=access_expires,
        user=_user_info(user),
    )


@router.post(
    "/refresh",
    response_model=AccessTokenOnly,
    summary="Получить новый access по refresh-токену",
)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> AccessTokenOnly:
    try:
        payload = auth_service.decode_token(body.refresh_token)
    except auth_service.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token",
        )

    if auth_service.is_blacklisted(payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    try:
        user_id = int(payload.sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    user = await auth_service.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing"
        )

    access_token, expires_in = auth_service.create_access_token(
        user.id, user.username, user.role_names
    )
    return AccessTokenOnly(
        access_token=access_token, token_type="bearer", expires_in=expires_in
    )


@router.post(
    "/logout",
    summary="Отзыв текущего access-токена (in-memory blacklist)",
)
async def logout(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = auth_service.decode_token(token)
    except auth_service.JWTError:
        # Already invalid — treat as success.
        return {"detail": "Logged out"}

    auth_service.blacklist_token(payload.jti)
    return {"detail": "Logged out"}


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Текущий пользователь",
)
async def me(user: User = Depends(get_current_user)) -> UserInfo:
    return _user_info(user)
