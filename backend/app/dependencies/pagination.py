"""Common Query-parameter dependencies."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


# Параметры пагинации: skip/limit передаются в каждый list-эндпоинт через Depends
@dataclass
class PaginationParams:
    skip: int
    limit: int


def get_pagination(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(50, ge=1, le=200, description="Размер страницы"),
) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)


# Флаг для включения «удалённых» (мягко) записей в выборку
def get_include_deleted(
    include_deleted: bool = Query(
        False,
        description="Показывать также удалённые (status='decommissioned'/'inactive'/'terminated')",
    ),
) -> bool:
    return include_deleted
