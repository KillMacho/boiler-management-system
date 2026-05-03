"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path

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
    personnel,
    requests,
    telemetry,
    warehouse,
    work_orders,
)
from app.services.reference_cache import reference_cache
from app.utils.logging_middleware import access_log_middleware

# Register all ORM mappers.
from app import models  # noqa: F401

logger = logging.getLogger("main")

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
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
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
