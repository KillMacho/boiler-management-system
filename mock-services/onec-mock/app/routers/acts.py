"""POST /hs/boiler/acts — accept work acts from backend."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import require_basic_auth
from app.schemas import ActsRequest, ActsResponse
from app.storage import storage

logger = logging.getLogger("onec_mock.acts")
router = APIRouter()


@router.post("/hs/boiler/acts", response_model=ActsResponse)
async def receive_acts(
    payload: ActsRequest,
    _user: str = Depends(require_basic_auth),
) -> ActsResponse:
    count = len(payload.акты)
    storage.add_acts(payload.период, payload.model_dump())
    logger.info("acts received: period=%s count=%d", payload.период, count)

    # Generate fake 1C document numbers: 8-digit zero-padded sequential strings
    doc_numbers = [str(i + 1).zfill(8) for i in range(count)]

    return ActsResponse(
        получено_актов=count,
        проведено_актов=count,
        номера_документов_1с=doc_numbers,
        сообщение=f"Акты за период {payload.период} успешно приняты в 1С",
    )
