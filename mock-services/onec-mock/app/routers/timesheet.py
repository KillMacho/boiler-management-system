"""POST /hs/boiler/timesheet — accept employee timesheets from backend."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import require_basic_auth
from app.schemas import TimesheetRequest, TimesheetResponse
from app.storage import storage

logger = logging.getLogger("onec_mock.timesheet")
router = APIRouter()


@router.post("/hs/boiler/timesheet", response_model=TimesheetResponse)
async def receive_timesheet(
    payload: TimesheetRequest,
    _user: str = Depends(require_basic_auth),
) -> TimesheetResponse:
    count = len(payload.табель)
    storage.add_timesheet(payload.период, payload.model_dump())
    logger.info("timesheet received: period=%s rows=%d", payload.период, count)
    return TimesheetResponse(получено_строк=count)
