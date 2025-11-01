from __future__ import annotations

from contextlib import asynccontextmanager
from inspect import iscoroutinefunction
from typing import Any, Callable, cast

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_use_lifo=settings.DB_POOL_USE_LIFO,
    )
    session_maker = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    app.state.db_engine = engine
    app.state.db_sessionmaker = session_maker
    try:
        yield
    finally:
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            close = getattr(redis, "close", None)
            if callable(close):
                if iscoroutinefunction(close):
                    await cast(Callable[[], Any], close)()
                else:
                    cast(Callable[[], Any], close)()
        except Exception:
            pass
        await engine.dispose()
