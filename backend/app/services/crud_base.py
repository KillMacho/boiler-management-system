"""Generic CRUD helper to remove copy-paste across 9 entity routers.

Soft-delete uses a configurable status string. Entities without a `status`
column fall back to hard delete.
"""
from __future__ import annotations

from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(
        self,
        model: Type[ModelT],
        *,
        soft_delete_status: Optional[str] = "decommissioned",
    ) -> None:
        self.model = model
        self.soft_delete_status = soft_delete_status

    @property
    def has_status(self) -> bool:
        return hasattr(self.model, "status")

    # -------- read -----------------------------------------------------------
    async def get(self, session: AsyncSession, id: Any) -> Optional[ModelT]:
        return await session.get(self.model, id)

    async def list(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_by: Any = None,
        extra_filters: Optional[Sequence] = None,
    ) -> List[ModelT]:
        stmt: Select = select(self.model)
        if (
            self.has_status
            and not include_deleted
            and self.soft_delete_status is not None
        ):
            stmt = stmt.where(self.model.status != self.soft_delete_status)  # type: ignore[attr-defined]
        if extra_filters:
            for cond in extra_filters:
                stmt = stmt.where(cond)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            pk = getattr(self.model, "id", None)
            if pk is not None:
                stmt = stmt.order_by(pk)
        stmt = stmt.offset(skip).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        return list(rows)

    # -------- write ----------------------------------------------------------
    async def create(
        self, session: AsyncSession, payload: CreateSchemaT
    ) -> ModelT:
        obj = self.model(**payload.model_dump(exclude_unset=False))
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def update(
        self, session: AsyncSession, obj: ModelT, payload: UpdateSchemaT
    ) -> ModelT:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def soft_delete(
        self, session: AsyncSession, obj: ModelT
    ) -> ModelT:
        if not self.has_status or self.soft_delete_status is None:
            await session.delete(obj)
            await session.commit()
            return obj
        setattr(obj, "status", self.soft_delete_status)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def hard_delete(self, session: AsyncSession, obj: ModelT) -> None:
        await session.delete(obj)
        await session.commit()
