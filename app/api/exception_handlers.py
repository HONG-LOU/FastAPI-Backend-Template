from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
import asyncpg

from app.core.context import get_request_id
from app.core.exceptions import AppException
from app.core.logging import get_logger


logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    message: str
    code: str
    request_id: str | None = None
    data: Any | None = None
    errors: list[dict[str, Any]] | None = None


def _error_response(
    status_code: int,
    *,
    message: str,
    code: str,
    data: Any | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        message=message,
        code=code,
        request_id=get_request_id(),
        data=data,
        errors=errors,
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _error_response(exc.status_code, message=str(exc.detail), code="http_error")


async def app_exception_handler(request: Request, exc: AppException):
    if exc.status_code >= 500:
        logger.exception("AppException: %s", exc.message)
    else:
        logger.warning("AppException: %s", exc.message)
    return _error_response(
        exc.status_code, message=exc.message, code=exc.code, data=exc.data
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    return _error_response(
        422, message="Validation error", code="validation_error", errors=exc.errors()
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    return _error_response(401, message="Invalid token", code="invalid_token")


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", str(exc))
    return _error_response(500, message="Internal Server Error", code="internal_error")


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("SQLAlchemy error: %s", str(exc))
    return _error_response(503, message="Database error", code="database_error")


async def asyncpg_exception_handler(request: Request, exc: asyncpg.PostgresError):
    logger.exception("Postgres error: %s", str(exc))
    return _error_response(
        503, message="Database unavailable", code="database_unavailable"
    )
