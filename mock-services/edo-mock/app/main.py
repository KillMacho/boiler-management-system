"""Mock EDO operator server (emulates Kontur.Extern API).

Accepts XML reports via multipart POST /api/v1/submission/upload (API Key auth).
Tracks document flow status with time-based state progression.
Admin endpoints at /admin/* (no auth) for demo inspection.
Port: 8081 (configurable via .env).
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request

from app.config import settings
from app.routers import admin, edo_status, submission

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("edo_mock")

# Ensure storage directory exists on startup
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Mock ЭДО Оператор (Контур.Экстерн)",
    description=(
        "Эмулятор HTTP API оператора электронного документооборота. "
        "Принимает XML-отчёты по форматам ФНС/ФСС/ПФР, хранит на диске, "
        "эмулирует прохождение документооборота (accepted → processing → confirmed). "
        "Реальная подпись (КЭП) и оператор подключаются при промышленном внедрении."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    size = request.headers.get("content-length", "?")
    response = await call_next(request)
    logger.info(
        "%s %s  status=%d  body=%s bytes",
        request.method, request.url.path, response.status_code, size,
    )
    return response


app.include_router(submission.router)
app.include_router(edo_status.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "mock-edo"}
