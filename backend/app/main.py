"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import AsyncSessionLocal
from app.routers import auth as auth_router
from app.routers import (
    audit,
    boilers,
    customers,
    integration,
    lookups,
    maintenance,
    monitoring,
    notifications,
    personnel,
    reporting,
    requests,
    telemetry,
    warehouse,
    work_orders,
)
from app.websocket import monitoring_ws
from app.services.reference_cache import reference_cache
from app.utils.logging_middleware import access_log_middleware

# Register all ORM mappers.
from app import models  # noqa: F401

logger = logging.getLogger("main")

# Configure detailed error logging to file
_log_dir = Path("logs")
_log_dir.mkdir(exist_ok=True)
_file_handler = logging.handlers.RotatingFileHandler(
    _log_dir / "database_errors.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
)
_file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logging.getLogger().addHandler(_file_handler)

app = FastAPI(
    title=settings.app_name,
    description="Информационная система управления котельной установкой — REST API",
    version="0.3.0",
    debug=settings.app_debug,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(access_log_middleware)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    tb_str = traceback.format_exc()
    logger.error(
        "Database error on %s %s\nException: %s\n%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        tb_str,
    )
    # Log the originating SQL if available
    if hasattr(exc, "statement"):
        logger.error("Failed SQL: %s", exc.statement)
    if hasattr(exc, "orig"):
        logger.error("Database driver error: %s", exc.orig)
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    tb_str = traceback.format_exc()
    logger.error(
        "Unhandled error on %s %s\nException: %s\n%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        tb_str,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    async with AsyncSessionLocal() as session:
        await reference_cache.warmup(session)
    Path("uploads/work_orders").mkdir(parents=True, exist_ok=True)
    logger.info("Application startup complete")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"], summary="Health check")
async def root() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": app.version}


@app.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok"}


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(boilers.router)
app.include_router(telemetry.router)
app.include_router(monitoring.router)
app.include_router(requests.router)
app.include_router(work_orders.router)
app.include_router(maintenance.router)
app.include_router(warehouse.router)
app.include_router(personnel.router)
app.include_router(customers.router)
app.include_router(audit.router)
app.include_router(lookups.router)
app.include_router(integration.router)
app.include_router(reporting.router)
app.include_router(notifications.router)
app.include_router(monitoring_ws.router)
