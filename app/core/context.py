from __future__ import annotations

from contextvars import ContextVar


# 每个请求的 Request ID
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# 每个请求的开始时间（perf 计时使用），单位：秒（time.perf_counter）
request_start_time_ctx_var: ContextVar[float | None] = ContextVar(
    "request_start_time", default=None
)


def get_request_id() -> str | None:
    return request_id_ctx_var.get()


def set_request_id(value: str | None) -> None:
    request_id_ctx_var.set(value)


def set_request_start_time(value: float | None) -> None:
    request_start_time_ctx_var.set(value)


def get_request_start_time() -> float | None:
    return request_start_time_ctx_var.get()
