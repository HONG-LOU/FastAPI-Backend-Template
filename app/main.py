from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.chat import router as chat_router
from app.api.exception_handlers import (
    http_exception_handler,
    app_exception_handler,
    validation_exception_handler,
    jwt_exception_handler,
    unhandled_exception_handler,
)
from app.core.exceptions import AppException
from app.api.middlewares import RequestContextMiddleware
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.APP_NAME)

    # CORS
    if settings.BACKEND_CORS_ORIGINS:
        # 支持通配：当为 ["*"] 时使用正则放通所有来源（兼容 allow_credentials=True）
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

    # Middlewares
    app.add_middleware(RequestContextMiddleware)

    # Routers
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])

    # Exception handlers
    from fastapi.exceptions import RequestValidationError
    from fastapi import HTTPException as FastAPIHTTPException

    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    from jose import JWTError

    app.add_exception_handler(JWTError, jwt_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
