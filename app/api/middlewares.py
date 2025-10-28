from __future__ import annotations

import time
import uuid
from starlette.types import ASGIApp, Scope, Receive, Send, Message

from app.core.context import set_request_id, set_request_start_time
from app.core.logging import get_logger


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        set_request_id(request_id)
        start = time.perf_counter()
        set_request_start_time(start)
        logger = get_logger("app.request")
        status_code: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            method = scope.get("method", "-")
            path = scope.get("path", "-")
            client = (scope.get("client") or (None, None))[0] or "-"
            ua = headers.get("user-agent", "-")[:200]
            logger.info(
                "%s %s -> %s %sms",
                method,
                path,
                status_code or 0,
                duration_ms,
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code or 0,
                    "duration_ms": duration_ms,
                    "client": client,
                    "user_agent": ua,
                },
            )
            set_request_id(None)
            set_request_start_time(None)
