"""POST /hs/boiler/transactions — accept accounting entries from backend."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import require_basic_auth
from app.schemas import TransactionsRequest, TransactionsResponse
from app.storage import storage

logger = logging.getLogger("onec_mock.transactions")
router = APIRouter()


@router.post("/hs/boiler/transactions", response_model=TransactionsResponse)
async def receive_transactions(
    payload: TransactionsRequest,
    _user: str = Depends(require_basic_auth),
) -> TransactionsResponse:
    count = len(payload.проводки)
    storage.add_transactions(payload.период, payload.model_dump())
    logger.info("transactions received: period=%s count=%d", payload.период, count)
    return TransactionsResponse(проведено_проводок=count)
