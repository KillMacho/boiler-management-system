"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth as auth_router

# Import models package to register all mappers (needed for relationship strings).
from app import models  # noqa: F401

app = FastAPI(
    title=settings.app_name,
    description="Информационная система управления котельной установкой — REST API",
    version="0.2.0",
    debug=settings.app_debug,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health check")
async def root() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": app.version}


@app.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router.router)
