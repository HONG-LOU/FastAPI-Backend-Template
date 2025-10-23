from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.config import settings
from app.core.context import get_request_id


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            data["request_id"] = rid
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            data.update(record.extra)
        indent = 2 if settings.LOG_JSON_PRETTY else None
        return json.dumps(
            data, ensure_ascii=False, separators=(",", ":"), indent=indent
        )


def _create_handler() -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        datefmt = "%Y-%m-%dT%H:%M:%S%z"
        handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    return handler


def configure_logging() -> None:
    root = logging.getLogger()
    # 清空可能已有的处理器，避免重复日志
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = _create_handler()
    root.addHandler(handler)

    level_name = settings.LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    # 降低冗长依赖库日志
    for noisy in [
        "uvicorn",
        "sqlalchemy.engine",
        "asyncpg",
        "alembic",
    ]:
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))
