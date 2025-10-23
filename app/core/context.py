from __future__ import annotations

from contextvars import ContextVar
from typing import Optional


# 每个请求的 Request ID
request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# 每个请求的开始时间（perf 计时使用），单位：秒（time.perf_counter）
request_start_time_ctx_var: ContextVar[Optional[float]] = ContextVar(
    "request_start_time", default=None
)


def get_request_id() -> Optional[str]:
    return request_id_ctx_var.get()


def set_request_id(value: Optional[str]) -> None:
    request_id_ctx_var.set(value)


def set_request_start_time(value: Optional[float]) -> None:
    request_start_time_ctx_var.set(value)


def get_request_start_time() -> Optional[float]:
    return request_start_time_ctx_var.get()
