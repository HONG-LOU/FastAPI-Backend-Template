from __future__ import annotations

from typing import Any


class AppException(Exception):
    __slots__ = ("message", "code", "status_code", "data")

    def __init__(
        self,
        message: str,
        *,
        code: int = 10000,
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
        code: int = 40401,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, data=data)


class Unauthorized(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        code: int = 40101,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class Forbidden(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        code: int = 40301,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403, data=data)


class BadRequest(AppException):
    def __init__(
        self,
        message: str = "Bad Request",
        *,
        code: int = 40001,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=400, data=data)


class Conflict(AppException):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        code: int = 40901,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=409, data=data)


class ServiceUnavailable(AppException):
    def __init__(
        self,
        message: str = "Service Unavailable",
        *,
        code: int = 50301,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=503, data=data)


class RegistrationError(AppException):
    def __init__(
        self,
        message: str = "Registration Error",
        *,
        code: int = 20001,
        status_code: int = 400,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code, data=data)


class CredentialsInvalid(AppException):
    def __init__(
        self,
        message: str = "Invalid credentials",
        *,
        code: int = 21001,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class TokenInvalid(AppException):
    def __init__(
        self,
        message: str = "Invalid token",
        *,
        code: int = 21002,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class TokenRevoked(AppException):
    def __init__(
        self,
        message: str = "Token revoked",
        *,
        code: int = 21003,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class TokenTypeMismatch(AppException):
    def __init__(
        self,
        message: str = "Token type mismatch",
        *,
        code: int = 21004,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class TokenMalformed(AppException):
    def __init__(
        self,
        message: str = "Token malformed",
        *,
        code: int = 21005,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=400, data=data)


class VerificationInvalid(AppException):
    def __init__(
        self,
        message: str = "Email verification invalid",
        *,
        code: int = 22001,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class VerificationExpired(AppException):
    def __init__(
        self,
        message: str = "Email verification expired",
        *,
        code: int = 22002,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=401, data=data)


class UserNotFound(NotFound):
    def __init__(
        self,
        message: str = "User not found",
        *,
        code: int = 24001,
        data: Any | None = None,
    ) -> None:
        super().__init__(message, code=code, data=data)