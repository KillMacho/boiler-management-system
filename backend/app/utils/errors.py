"""HTTPException factory helpers."""
from __future__ import annotations

from fastapi import HTTPException, status


def not_found(entity: str, entity_id: object | None = None) -> HTTPException:
    detail = f"{entity} not found" if entity_id is None else f"{entity} {entity_id} not found"
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def forbidden(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def payload_too_large(detail: str = "Payload too large") -> HTTPException:
    return HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=detail)


def unsupported_media(detail: str = "Unsupported media type") -> HTTPException:
    return HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detail)
