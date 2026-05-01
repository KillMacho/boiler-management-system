"""Shared Pydantic config: from_attributes=True for ORM mapping."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    """Base for response schemas that read from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class CamelOrmModel(OrmModel):
    """OrmModel that also serialises with camelCase keys (for JS clients)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
