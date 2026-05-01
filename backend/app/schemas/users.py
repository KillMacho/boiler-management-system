"""Pydantic schemas: users, roles, audit_log, user_roles."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import OrmModel


# -------- roles ---------------------------------------------------------------
class RoleBase(BaseModel):
    name: str = Field(max_length=50)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)


class RoleResponse(RoleBase, OrmModel):
    id: int


# -------- users ---------------------------------------------------------------
class UserBase(BaseModel):
    username: str = Field(max_length=100)
    employee_id: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, max_length=100)
    employee_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class UserResponse(UserBase, OrmModel):
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    roles: List[str] = Field(default_factory=list)


# -------- user_roles (junction) ----------------------------------------------
class UserRoleBase(BaseModel):
    user_id: int
    role_id: int


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleResponse(UserRoleBase, OrmModel):
    pass


# -------- audit_log -----------------------------------------------------------
class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    action: str = Field(max_length=100)
    entity_type: str = Field(max_length=100)
    entity_id: Optional[str] = Field(default=None, max_length=100)
    details: Optional[str] = None  # JSON string


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase, OrmModel):
    id: int
    timestamp: datetime
