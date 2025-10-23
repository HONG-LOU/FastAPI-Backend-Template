from __future__ import annotations

from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status_code: int = 400,
        data: Optional[Any] = None,
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
        data: Optional[Any] = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, data=data)


class Unauthorized(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        code: str = "unauthorized",
        data: Optional[Any] = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class Forbidden(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        code: str = "forbidden",
        data: Optional[Any] = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403, data=data)
