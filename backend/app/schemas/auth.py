"""Auth-related schemas: login, tokens, user info."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import OrmModel


class LoginRequest(BaseModel):
    """Used for the JSON variant of login. The OAuth2-form flow uses
    OAuth2PasswordRequestForm directly in the route."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(OrmModel):
    id: int
    username: str
    employee_id: Optional[int] = None
    is_active: bool
    last_login: Optional[datetime] = None
    roles: List[str] = Field(default_factory=list)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds for access token
    user: UserInfo


class AccessTokenOnly(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Decoded JWT body."""

    model_config = ConfigDict(extra="ignore")

    sub: str  # user_id as string
    username: str
    roles: List[str] = Field(default_factory=list)
    type: str  # "access" | "refresh"
    exp: int
    jti: str  # token id, for blacklisting
