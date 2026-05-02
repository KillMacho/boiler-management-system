"""Audit log read-only endpoint, restricted to chief_engineer/dispatcher."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import RoleChecker
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.users import AuditLog
from app.schemas.users import AuditLogResponse
from app.services.permissions import AUDIT_READ

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"],
    dependencies=[Depends(RoleChecker(AUDIT_READ))],
)


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())
