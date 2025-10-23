from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import (
    set_request_id,
    set_request_start_time,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        set_request_id(request_id)

        start = time.perf_counter()
        set_request_start_time(start)
        try:
            response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            set_request_id(None)
            set_request_start_time(None)

        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(duration_ms)
        return response
