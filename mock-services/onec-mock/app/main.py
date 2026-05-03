"""Mock 1C:Enterprise HTTP-service server.

Exposes /hs/boiler/* endpoints with Basic Auth to emulate real 1C behavior.
Admin endpoints at /admin/* (no auth) for demo inspection.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import acts, admin, materials, payslips, timesheet, transactions

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("onec_mock")

app = FastAPI(
    title="Mock 1С:Предприятие HTTP-сервис",
    description=(
        "Эмулятор HTTP-сервисов 1С для разработки и тестирования backend-интеграции. "
        "Принимает данные по адресу /hs/boiler/*, хранит в памяти, "
        "отдаёт через /admin/received/*."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Access log middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body_size = request.headers.get("content-length", "?")
    response = await call_next(request)
    logger.info(
        "%s %s  status=%d  body=%s bytes",
        request.method,
        request.url.path,
        response.status_code,
        body_size,
    )
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(acts.router, tags=["1С / Акты"])
app.include_router(materials.router, tags=["1С / Материалы"])
app.include_router(transactions.router, tags=["1С / Проводки"])
app.include_router(timesheet.router, tags=["1С / Табель"])
app.include_router(payslips.router, tags=["1С / Расчётные листки"])
app.include_router(admin.router)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"статус": "ok", "сервис": "mock-1C"}
