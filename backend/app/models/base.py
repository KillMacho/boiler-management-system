"""Declarative Base for all ORM models.

Naming convention is set so Alembic-generated constraint names match the
existing database (CK_*, FK_*, IX_*, UQ_*, PK_*).
"""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "IX_%(table_name)s_%(column_0_label)s",
    "uq": "UQ_%(table_name)s_%(column_0_name)s",
    "ck": "CK_%(table_name)s_%(constraint_name)s",
    "fk": "FK_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "PK_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
