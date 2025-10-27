from __future__ import annotations

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast

from app.core.context import get_request_id


F = TypeVar("F", bound=Callable[..., Any])


def log_exceptions(logger: logging.Logger | None = None) -> Callable[[F], F]:
    _logger = logger or logging.getLogger(__name__)

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                try:
                    return await cast(Callable[..., Awaitable[Any]], func)(
                        *args, **kwargs
                    )
                except Exception:  # noqa: BLE001
                    rid = get_request_id()
                    _logger.exception("Unhandled in %s rid=%s", func.__name__, rid)
                    raise

            return cast(F, async_wrapper)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any):
            try:
                return func(*args, **kwargs)
            except Exception:  # noqa: BLE001
                rid = get_request_id()
                _logger.exception("Unhandled in %s rid=%s", func.__name__, rid)
                raise

        return cast(F, sync_wrapper)

    return decorator


def record_timing(metric_name: str) -> Callable[[F], F]:
    logger = logging.getLogger("timing")

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                start = time.perf_counter()
                try:
                    return await cast(Callable[..., Awaitable[Any]], func)(
                        *args, **kwargs
                    )
                finally:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    rid = get_request_id()
                    logger.info(
                        "metric=%s duration_ms=%s rid=%s", metric_name, duration_ms, rid
                    )

            return cast(F, async_wrapper)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = int((time.perf_counter() - start) * 1000)
                rid = get_request_id()
                logger.info(
                    "metric=%s duration_ms=%s rid=%s", metric_name, duration_ms, rid
                )

        return cast(F, sync_wrapper)

    return decorator
