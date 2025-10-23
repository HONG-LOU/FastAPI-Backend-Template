from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="", case_sensitive=False
    )

    APP_NAME: str = "Career Fair API"
    APP_ENV: str = "dev"

    SECRET_KEY: str = Field(..., description="JWT 密钥")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = Field(
        ..., description="postgresql+asyncpg://user:pass@host:port/db"
    )

    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=list)

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO", description="日志等级，例如 INFO/DEBUG/WARN/ERROR"
    )
    LOG_FORMAT: str = Field(default="json", description="日志格式：json 或 console")
    LOG_JSON_PRETTY: bool = Field(
        default=False, description="开发环境下是否美化 JSON 日志"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        # 支持逗号分隔字符串或 JSON 数组
        if v is None or v == "":
            return []
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                # 让 pydantic 继续解析 JSON
                return s
            return [i.strip() for i in s.split(",") if i.strip()]
        return v

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def normalize_log_format(cls, v):
        if isinstance(v, str):
            vv = v.strip().lower()
            if vv in {"json", "console"}:
                return vv
        return "json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
