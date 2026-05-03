"""Admin endpoints — no auth required, for inspection during demo/testing."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.storage import storage

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/received/acts", summary="All received acts (by period)")
async def get_received_acts() -> dict:
    return storage.get_acts()


@router.get("/received/materials", summary="All received material movements (by period)")
async def get_received_materials() -> dict:
    return storage.get_materials()


@router.get("/received/transactions", summary="All received transactions (by period)")
async def get_received_transactions() -> dict:
    return storage.get_transactions()


@router.get("/received/timesheet", summary="All received timesheets (by period)")
async def get_received_timesheet() -> dict:
    return storage.get_timesheet()


@router.get("/received/payslips", summary="All received payslip requests (by period)")
async def get_received_payslips() -> dict:
    return storage.get_payslips()


@router.get("/stats", summary="Document counts by type")
async def get_stats() -> dict:
    return storage.stats()


@router.delete("/received/clear", summary="Clear all in-memory data (for repeated tests)")
async def clear_all() -> dict:
    storage.clear()
    return {"статус": "ok", "сообщение": "Все данные очищены"}
