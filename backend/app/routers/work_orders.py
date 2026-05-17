"""Work orders router: list, my, start, complete, photos, checklist."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.dependencies.auth import RoleChecker, get_current_user
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.personnel import Brigade, BrigadeMember
from app.models.requests import WorkOrder
from app.schemas.requests import (
    WorkOrderChecklistItemResponse,
    WorkOrderPhotoResponse,
    WorkOrderResponse,
)
from app.services import work_order_service
from app.services.permissions import READ_ANY, WORK_ORDER_WRITE
from app.utils.errors import not_found, payload_too_large, unsupported_media

router = APIRouter(prefix="/api/v1/work-orders", tags=["work-orders"])

# Фото нарядов хранятся на диске; допустимы только JPEG/PNG до 10 МБ
UPLOAD_ROOT = Path("uploads/work_orders")
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB


class CompletePayload(BaseModel):
    notes: Optional[str] = None
    total_amount: Optional[float] = Field(default=0.0, ge=0)


class ChecklistTogglePayload(BaseModel):
    is_completed: bool


@router.get("/", response_model=List[WorkOrderResponse], dependencies=[Depends(RoleChecker(READ_ANY))])
async def list_work_orders(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    brigade_id: Optional[int] = Query(None),
    request_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(WorkOrder)
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    if brigade_id is not None:
        stmt = stmt.where(WorkOrder.brigade_id == brigade_id)
    if request_id is not None:
        stmt = stmt.where(WorkOrder.request_id == request_id)
    stmt = stmt.order_by(WorkOrder.assigned_at.desc()).offset(pagination.skip).limit(pagination.limit)
    return list((await session.execute(stmt)).scalars().all())


@router.get("/my", response_model=List[WorkOrderResponse])
async def list_my_work_orders(
    pagination: PaginationParams = Depends(get_pagination),
    session: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Возвращает наряды бригад, в которых состоит сотрудник текущего пользователя.

    Если у пользователя нет связанного сотрудника — пустой список.
    """
    if user.employee_id is None:
        return []
    led_stmt = select(Brigade.id).where(Brigade.leader_employee_id == user.employee_id)
    member_stmt = select(BrigadeMember.brigade_id).where(BrigadeMember.employee_id == user.employee_id)
    led_ids = list((await session.execute(led_stmt)).scalars().all())
    member_ids = list((await session.execute(member_stmt)).scalars().all())
    brigade_ids = list({*led_ids, *member_ids})
    return await work_order_service.list_my_brigade_work_orders(
        session, brigade_ids=brigade_ids, skip=pagination.skip, limit=pagination.limit
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse, dependencies=[Depends(RoleChecker(READ_ANY))])
async def get_work_order(work_order_id: int, session: AsyncSession = Depends(get_db)):
    obj = await session.get(WorkOrder, work_order_id)
    if obj is None:
        raise not_found("work_order", work_order_id)
    return obj


@router.get(
    "/{work_order_id}/checklist",
    response_model=List[WorkOrderChecklistItemResponse],
    dependencies=[Depends(RoleChecker(READ_ANY))],
)
async def list_checklist(work_order_id: int, session: AsyncSession = Depends(get_db)):
    from app.models.requests import WorkOrderChecklistItem
    rows = (await session.execute(
        select(WorkOrderChecklistItem)
        .where(WorkOrderChecklistItem.work_order_id == work_order_id)
        .order_by(WorkOrderChecklistItem.sort_order)
    )).scalars().all()
    return list(rows)


@router.get(
    "/{work_order_id}/photos",
    response_model=List[WorkOrderPhotoResponse],
    dependencies=[Depends(RoleChecker(READ_ANY))],
)
async def list_photos(work_order_id: int, session: AsyncSession = Depends(get_db)):
    from app.models.requests import WorkOrderPhoto
    rows = (await session.execute(
        select(WorkOrderPhoto)
        .where(WorkOrderPhoto.work_order_id == work_order_id)
        .order_by(WorkOrderPhoto.uploaded_at.desc())
    )).scalars().all()
    return list(rows)


@router.post("/{work_order_id}/start", response_model=WorkOrderResponse)
async def start_work_order(
    work_order_id: int,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WORK_ORDER_WRITE)),
):
    return await work_order_service.start(session, work_order_id=work_order_id, user_id=user.id)


@router.post("/{work_order_id}/complete", response_model=WorkOrderResponse)
async def complete_work_order(
    work_order_id: int,
    payload: CompletePayload = Body(default_factory=CompletePayload),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WORK_ORDER_WRITE)),
):
    from decimal import Decimal

    return await work_order_service.complete(
        session,
        work_order_id=work_order_id,
        user_id=user.id,
        notes=payload.notes,
        total_amount=Decimal(str(payload.total_amount or 0)),
    )


@router.post(
    "/{work_order_id}/checklist/{item_id}",
    response_model=WorkOrderChecklistItemResponse,
)
async def toggle_checklist_item(
    work_order_id: int,
    item_id: int,
    payload: ChecklistTogglePayload,
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WORK_ORDER_WRITE)),
):
    return await work_order_service.toggle_checklist_item(
        session,
        work_order_id=work_order_id,
        item_id=item_id,
        is_completed=payload.is_completed,
        user_id=user.id,
    )


@router.post(
    "/{work_order_id}/photos",
    response_model=WorkOrderPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_work_order_photo(
    work_order_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    user=Depends(RoleChecker(WORK_ORDER_WRITE)),
):
    # Verify work order exists
    wo = await session.get(WorkOrder, work_order_id)
    if wo is None:
        raise not_found("work_order", work_order_id)

    # Читаем на 1 байт больше лимита, чтобы обнаружить превышение без полной загрузки
    data = await file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise payload_too_large(f"Max {MAX_PHOTO_BYTES} bytes")

    # Проверяем реальный формат через Pillow — защита от подмены расширения
    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()  # checks integrity
            img_format = img.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise unsupported_media("File is not a valid image")
    if img_format not in ALLOWED_IMAGE_FORMATS:
        raise unsupported_media(f"Allowed formats: {sorted(ALLOWED_IMAGE_FORMATS)}")

    ext = ".jpg" if img_format == "JPEG" else ".png"
    folder = UPLOAD_ROOT / str(work_order_id)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    target = folder / filename
    await run_in_threadpool(target.write_bytes, data)

    relative = target.as_posix()
    photo = await work_order_service.add_photo(
        session, work_order_id=work_order_id, file_path=relative, user_id=user.id
    )
    return photo
