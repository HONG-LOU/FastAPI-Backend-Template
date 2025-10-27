from __future__ import annotations

from typing import Any, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_request_id
from app.core.exceptions import AppException
from app.core.logging import get_logger


logger = get_logger(__name__)


def _base_payload(message: str, code: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": message, "code": code}
    rid = get_request_id()
    if rid:
        payload["request_id"] = rid
    return payload


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    payload = _base_payload(str(exc.detail), "http_error")
    return JSONResponse(status_code=exc.status_code, content=payload)


async def app_exception_handler(request: Request, exc: AppException):
    if exc.status_code >= 500:
        logger.exception("AppException: %s", exc.message)
    else:
        logger.warning("AppException: %s", exc.message)
    payload = _base_payload(exc.message, exc.code)
    if exc.data is not None:
        payload["data"] = exc.data
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(request: Request, exc: ValidationError):
    payload = _base_payload("Validation error", "validation_error")
    payload["errors"] = exc.errors()
    return JSONResponse(status_code=422, content=payload)


async def jwt_exception_handler(request: Request, exc: JWTError):
    payload = _base_payload("Invalid token", "invalid_token")
    return JSONResponse(status_code=401, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", str(exc))
    payload = _base_payload("Internal Server Error", "internal_error")
    return JSONResponse(status_code=500, content=payload)
