"""POST /hs/boiler/materials — accept material movements from backend."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import require_basic_auth
from app.schemas import MaterialsRequest, MaterialsResponse
from app.storage import storage

logger = logging.getLogger("onec_mock.materials")
router = APIRouter()


@router.post("/hs/boiler/materials", response_model=MaterialsResponse)
async def receive_materials(
    payload: MaterialsRequest,
    _user: str = Depends(require_basic_auth),
) -> MaterialsResponse:
    count = len(payload.движения_материалов)
    storage.add_materials(payload.период, payload.model_dump())
    logger.info("materials received: period=%s count=%d", payload.период, count)
    return MaterialsResponse(получено=count, проведено=count)
