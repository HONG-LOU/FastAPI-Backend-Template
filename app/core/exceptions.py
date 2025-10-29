from __future__ import annotations

from typing import Any


class AppException(Exception):
    __slots__ = ("message", "code", "status_code", "data")

    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status_code: int = 400,
        data: Any | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class NotFound(AppException):
    def __init__(
        self,
        message: str = "Not Found",
        *,
        code: str = "not_found",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, data=data)


class Unauthorized(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        code: str = "unauthorized",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class Forbidden(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        code: str = "forbidden",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403, data=data)


class BadRequest(AppException):
    def __init__(
        self,
        message: str = "Bad Request",
        *,
        code: str = "bad_request",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=400, data=data)


class Conflict(AppException):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        code: str = "conflict",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=409, data=data)


class ServiceUnavailable(AppException):
    def __init__(
        self,
        message: str = "Service Unavailable",
        *,
        code: str = "service_unavailable",
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=503, data=data)
