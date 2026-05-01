"""JWT, password hashing, token blacklist.

The blacklist is a simple in-memory set of jti (JWT id) values. It does not
persist across restarts — sufficient for a single-instance dev/study deployment.
For production swap with Redis or a DB-backed blacklist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Set

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.users import User
from app.schemas.auth import TokenPayload

# bcrypt is the only scheme we need; passlib auto-picks rounds.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory blacklist of revoked token jti values.
_blacklist: Set[str] = set()


# ----------------------------- passwords ------------------------------------
def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        # Malformed hash etc. — treat as failure.
        return False


# ----------------------------- tokens ---------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(
    *,
    user_id: int,
    username: str,
    roles: Iterable[str],
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, str, int]:
    """Return (encoded_jwt, jti, expires_in_seconds)."""
    expire = _now() + expires_delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "username": username,
        "roles": list(roles),
        "type": token_type,
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    encoded = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded, jti, int(expires_delta.total_seconds())


def create_access_token(
    user_id: int, username: str, roles: Iterable[str]
) -> tuple[str, int]:
    token, _, expires_in = _create_token(
        user_id=user_id,
        username=username,
        roles=roles,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token, expires_in


def create_refresh_token(
    user_id: int, username: str, roles: Iterable[str]
) -> tuple[str, int]:
    token, _, expires_in = _create_token(
        user_id=user_id,
        username=username,
        roles=roles,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    return token, expires_in


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT signature + expiry. Raises JWTError on failure."""
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    return TokenPayload(**payload)


def is_blacklisted(jti: str) -> bool:
    return jti in _blacklist


def blacklist_token(jti: str) -> None:
    _blacklist.add(jti)


# ----------------------------- user lookup ----------------------------------
async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession, username: str, password: str
) -> Optional[User]:
    user = await get_user_by_username(session, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


__all__ = [
    "JWTError",
    "authenticate_user",
    "blacklist_token",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_user_by_id",
    "get_user_by_username",
    "hash_password",
    "is_blacklisted",
    "verify_password",
]
