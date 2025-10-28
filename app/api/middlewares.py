from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Awaitable

from fastapi import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import (
    set_request_id,
    set_request_start_time,
)
from app.core.logging import get_logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        set_request_id(request_id)

        start = time.perf_counter()
        set_request_start_time(start)
        logger = get_logger("app.request")
        try:
            response: Response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            set_request_id(None)
            set_request_start_time(None)

        try:
            client = request.client.host if request.client else "-"
            ua = request.headers.get("user-agent", "-")
            logger.info(
                "%s %s -> %s %sms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client": client,
                    "user_agent": ua[:200],
                },
            )
        except Exception:
            # 访问日志不应影响主流程
            pass
        return response
