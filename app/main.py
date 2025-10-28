from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import cast
from starlette.types import ExceptionHandler as StarletteExceptionHandler
from starlette.middleware import Middleware

from app.core.config import settings
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.chat import router as chat_router
from app.api.routers.profile import router as profile_router
from app.api.exception_handlers import (
    http_exception_handler,
    app_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
    sqlalchemy_exception_handler,
    asyncpg_exception_handler,
)
from app.core.exceptions import AppException
from app.api.middlewares import RequestContextMiddleware
from app.core.logging import configure_logging
from sqlalchemy.exc import SQLAlchemyError


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        middleware=[Middleware(RequestContextMiddleware)],
    )

    # CORS
    if settings.BACKEND_CORS_ORIGINS:
        if settings.BACKEND_CORS_ORIGINS == ["*"]:
            app.add_middleware(
                CORSMiddleware,
                allow_origin_regex=".*",
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        else:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.BACKEND_CORS_ORIGINS,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

    # Routers
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(profile_router, prefix="/api/profile", tags=["profile"])

    # Exception handlers
    from fastapi.exceptions import RequestValidationError
    from fastapi import HTTPException as FastAPIHTTPException

    app.add_exception_handler(
        FastAPIHTTPException, cast(StarletteExceptionHandler, http_exception_handler)
    )
    app.add_exception_handler(
        AppException, cast(StarletteExceptionHandler, app_exception_handler)
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(StarletteExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(
        Exception, cast(StarletteExceptionHandler, unhandled_exception_handler)
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
    return app


app = create_app()
