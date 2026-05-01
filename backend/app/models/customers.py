"""Контрагенты (заказчики)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
