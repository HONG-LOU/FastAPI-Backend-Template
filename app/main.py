from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from app.core.config import settings
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.chat import router as chat_router
from app.api.routers.profile import router as profile_router
from app.api.exception_handlers import register_exception_handlers
from app.api.middlewares import RequestContextMiddleware
from app.core.logging import configure_logging
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        swagger_ui_parameters={
            "tryItOutEnabled": True,
            "defaultModelsExpandDepth": -1,
        },
        middleware=[Middleware(RequestContextMiddleware)],
        lifespan=lifespan,
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

    register_exception_handlers(app)
    return app


app = create_app()
