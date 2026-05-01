"""Pydantic schemas: customers."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import OrmModel


class CustomerBase(BaseModel):
    name: str = Field(max_length=300)
    inn: str = Field(min_length=10, max_length=12)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    contact_email: Optional[EmailStr] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=300)
    inn: Optional[str] = Field(default=None, min_length=10, max_length=12)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    contact_email: Optional[EmailStr] = None


class CustomerResponse(CustomerBase, OrmModel):
    id: int
