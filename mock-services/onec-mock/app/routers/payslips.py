"""POST /hs/boiler/payslips — generate fake payslips for requested period."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import require_basic_auth
from app.schemas import PayslipItem, PayslipsRequest, PayslipsResponse
from app.storage import storage

logger = logging.getLogger("onec_mock.payslips")
router = APIRouter()

# Fake employee roster used when the real timesheet data hasn't been received yet
_FAKE_EMPLOYEES = [
    (1, "Иванов И.И.", 65000.0),
    (2, "Петров П.П.", 58000.0),
    (3, "Сидорова А.В.", 72000.0),
    (4, "Козлов Д.Н.", 61000.0),
    (5, "Новикова Е.С.", 55000.0),
]


@router.post("/hs/boiler/payslips", response_model=PayslipsResponse)
async def receive_payslips(
    payload: PayslipsRequest,
    _user: str = Depends(require_basic_auth),
) -> PayslipsResponse:
    period = payload.период

    # Build payslips from timesheet data if available, else use fake roster
    ts_records = storage.timesheet.get(period, [])
    if ts_records:
        rows = ts_records[-1].data.get("табель", [])
        employees = [
            (r["сотрудник_id"], r["сотрудник_фио"], round(r["обычные_часы"] * 400, 2))
            for r in rows
        ]
    else:
        employees = _FAKE_EMPLOYEES

    листки = [
        PayslipItem(
            сотрудник_id=emp_id,
            сотрудник_фио=fio,
            период=period,
            к_выплате=amount,
            ссылка_pdf=f"/tmp/payslips/{period}/employee_{emp_id}.pdf",
        )
        for emp_id, fio, amount in employees
    ]

    storage.add_payslips(period, payload.model_dump())
    logger.info("payslips generated: period=%s count=%d", period, len(листки))

    return PayslipsResponse(сформировано=len(листки), расчётные_листки=листки)
