from functools import lru_cache
from typing import Literal, cast
from collections.abc import Sequence

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="", case_sensitive=False
    )

    APP_NAME: str = "Career Fair API"
    APP_ENV: str = "dev"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    VERIFY_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str

    # DB pool
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 80
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_USE_LIFO: bool = True

    # Redis
    REDIS_URL: str

    BACKEND_CORS_ORIGINS: list[str] = []

    # Public URLs
    FRONTEND_BASE_URL: str | None = None
    BACKEND_PUBLIC_BASE_URL: str | None = None

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_ALLOWED_HD: str | None = None

    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: str | None = None
    LINKEDIN_CLIENT_SECRET: str | None = None
    LINKEDIN_REDIRECT_URI: str | None = None

    # Mail
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_STARTTLS: bool = True
    MAIL_FROM: str | None = None

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    LOG_JSON_PRETTY: bool = False

    UPLOAD_DIR: str = "uploads"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                return cast(list[str], __import__("json").loads(s))
            return [item.strip() for item in s.split(",") if item.strip()]
        if isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
            items: Sequence[object] = cast(Sequence[object], v)
            return [str(item).strip() for item in items if str(item).strip()]
        return []

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def normalize_log_format(cls, v: object) -> str:
        if isinstance(v, str):
            vv = v.strip().lower()
            if vv in {"json", "console"}:
                return vv
        return "json"


@lru_cache
def get_settings() -> Settings:
    # fill config from environment variables at runtime, ignore missing required fields for static check
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()
