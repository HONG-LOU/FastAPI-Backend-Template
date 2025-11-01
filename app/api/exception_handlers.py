from __future__ import annotations

from typing import Any, Sequence, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.context import get_request_id
from app.core.exceptions import AppException
from app.core.logging import get_logger


logger = get_logger(__name__)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, Exception):
        return str(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True)
    if isinstance(obj, (list, tuple, set)):
        seq = cast(Sequence[Any], obj)
        return [_jsonable(x) for x in seq]
    if isinstance(obj, dict):
        d = cast(dict[str, Any], obj)
        return {k: _jsonable(v) for k, v in d.items()}
    return obj


class ErrorResponse(BaseModel):
    message: str
    code: int
    request_id: str | None = None
    data: Any | None = None
    errors: list[Any] | None = None


def _error_response(
    status_code: int,
    *,
    message: str,
    code: int,
    data: Any | None = None,
    errors: list[Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        message=message,
        code=code,
        request_id=get_request_id(),
        data=_jsonable(data) if data is not None else None,
        errors=_jsonable(errors) if errors is not None else None,
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _error_response(
        exc.status_code, message=str(exc.detail), code=10000 + exc.status_code
    )


async def app_exception_handler(request: Request, exc: AppException):
    if exc.status_code >= 500:
        logger.exception("AppException[%s]: %s", exc.code, exc.message)
    else:
        logger.warning("AppException[%s]: %s", exc.code, exc.message)
    return _error_response(
        exc.status_code, message=exc.message, code=exc.code, data=exc.data
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    errs = _jsonable(exc.errors())
    return _error_response(422, message="Validation error", code=11001, errors=errs)


async def global_exception_handler(request: Request, exc: Exception):
    try:
        path = request.url.path
    except Exception:
        path = "-"
    logger.exception("Unhandled exception at %s: %s", path, str(exc))
    return _error_response(500, message="Internal Server Error", code=19000)


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("SQLAlchemy error: %s", str(exc))
    return _error_response(503, message="Database error", code=12001)


async def asyncpg_exception_handler(request: Request, exc: Any):
    logger.exception("Postgres error: %s", str(exc))
    return _error_response(503, message="Database unavailable", code=12002)


def register_exception_handlers(app: FastAPI) -> None:
    from fastapi.exceptions import RequestValidationError
    from fastapi import HTTPException as FastAPIHTTPException
    from starlette.types import ExceptionHandler as StarletteExceptionHandler

    app.add_exception_handler(
        FastAPIHTTPException,  # type: ignore[arg-type]
        cast(StarletteExceptionHandler, http_exception_handler),
    )
    app.add_exception_handler(
        AppException, cast(StarletteExceptionHandler, app_exception_handler)
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(StarletteExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(
        Exception, cast(StarletteExceptionHandler, global_exception_handler)
    )
    app.add_exception_handler(
        SQLAlchemyError, cast(StarletteExceptionHandler, sqlalchemy_exception_handler)
    )
    try:
        import asyncpg as _asyncpg  # type: ignore[reportMissingTypeStubs]

        app.add_exception_handler(
            _asyncpg.PostgresError,
            cast(StarletteExceptionHandler, asyncpg_exception_handler),
        )
    except Exception:
        pass
