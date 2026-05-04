"""WebSocket endpoint for real-time monitoring updates.

Clients connect to /ws/monitoring?token=<jwt> and receive JSON frames:
  {"type": "telemetry_update", "boiler_id": ..., "timestamp": ..., "status": ..., "parameters": {...}, "breaches": [...]}
  {"type": "full_status", "boilers": [...]}  — sent once on connect
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from app.config import settings
from app.services.monitoring_service import StatusCache

logger = logging.getLogger("monitoring_ws")
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected, total=%d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected, total=%d", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        if not self._connections:
            return
        data = json.dumps(message, default=str, ensure_ascii=False)
        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections.discard(ws)

    async def send_personal(self, ws: WebSocket, message: dict) -> None:
        data = json.dumps(message, default=str, ensure_ascii=False)
        await ws.send_text(data)

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def _verify_token(token: str) -> bool:
    """Return True if token is a valid non-expired access JWT."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("type") == "access"
    except JWTError:
        return False


@router.websocket("/ws/monitoring")
async def monitoring_websocket(
    ws: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    if not _verify_token(token):
        await ws.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(ws)

    # Send full current status on connect
    cache = StatusCache.all()
    await manager.send_personal(ws, {
        "type": "full_status",
        "timestamp": time.time(),
        "boilers": [
            {"boiler_id": bid, **snap}
            for bid, snap in cache.items()
        ],
    })

    try:
        # Keep connection alive, echo pings
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                if msg == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await ws.send_text(json.dumps({"type": "heartbeat", "timestamp": time.time()}))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


async def broadcast_telemetry_update(
    boiler_id: int,
    timestamp,
    status: str,
    parameters: dict,
    breaches: list,
    auto_request_id=None,
) -> None:
    """Called from telemetry router after each successful ingest."""
    if manager.count == 0:
        return
    await manager.broadcast({
        "type": "telemetry_update",
        "boiler_id": boiler_id,
        "timestamp": str(timestamp),
        "status": status,
        "parameters": parameters,
        "breaches": breaches,
        "auto_request_id": auto_request_id,
    })
