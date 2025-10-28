from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, cast

from app.core.config import settings
from app.core.context import get_request_id


ANSI_RESET = "\x1b[0m"
ANSI_DIM = "\x1b[2m"
ANSI_BOLD = "\x1b[1m"
ANSI_COLORS = {
    "DEBUG": "\x1b[36m",  # cyan
    "INFO": "\x1b[32m",  # green
    "WARNING": "\x1b[33m",  # yellow
    "ERROR": "\x1b[31m",  # red
    "CRITICAL": "\x1b[35m",  # magenta
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        data: dict[str, Any] = {
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
        extras_obj = getattr(record, "ipdn_extra", None)
        if isinstance(extras_obj, dict):
            extras_any: dict[Any, Any] = cast(dict[Any, Any], extras_obj)
            extras_typed: dict[str, Any] = {str(k): v for k, v in extras_any.items()}
            data.update(extras_typed)
        indent = 2 if settings.LOG_JSON_PRETTY else None
        return json.dumps(
            data, ensure_ascii=False, separators=(",", ":"), indent=indent
        )


class ColorConsoleFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(fmt="%(message)s")

    def _supports_color(self) -> bool:
        return sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        rid = get_request_id()
        level = record.levelname
        color = ANSI_COLORS.get(level, "") if self._supports_color() else ""
        reset = ANSI_RESET if color else ""
        dim = ANSI_DIM if color else ""
        bold = ANSI_BOLD if color else ""

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        name = record.name
        msg = record.getMessage()

        segments = [
            f"{dim}{ts}{reset}",
            f"{bold}{color}{level:<8}{reset}",
            f"{dim}[{name}]{reset}",
            msg,
        ]
        if rid:
            segments.append(f"{dim}rid={rid}{reset}")

        extras_obj = getattr(record, "ipdn_extra", None)
        if isinstance(extras_obj, dict):
            extras_any: dict[Any, Any] = cast(dict[Any, Any], extras_obj)
            extras_typed: dict[str, Any] = {str(k): v for k, v in extras_any.items()}
            extras_list: list[str] = []
            for k, v in extras_typed.items():
                extras_list.append(f"{k}={v}")
            if extras_list:
                segments.append(f"{dim}{' '.join(extras_list)}{reset}")

        s = " ".join(segments)
        if record.exc_info:
            s += "\n" + self.formatException(record.exc_info)
        return s


class ContextLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    def __init__(
        self, logger: logging.Logger, extra: dict[str, Any] | None = None
    ) -> None:
        super().__init__(logger, extra or {})

    def process(self, msg: Any, kwargs: dict[str, Any]):  # type: ignore[override]
        fields = kwargs.pop("extra", None)
        if fields is None:
            fields = {}
        base_extra: dict[str, Any] = cast(dict[str, Any], dict(self.extra or {}))
        if fields:
            merged_fields: dict[str, Any] = {**base_extra, **fields}
        else:
            merged_fields = base_extra
        kwargs["extra"] = {"ipdn_extra": merged_fields}
        return msg, kwargs

    def with_fields(self, **fields: Any) -> "ContextLoggerAdapter":
        base_extra: dict[str, Any] = cast(dict[str, Any], dict(self.extra or {}))
        merged: dict[str, Any] = {**base_extra, **fields}
        return ContextLoggerAdapter(self.logger, merged)


def get_logger(name: str | None = None) -> ContextLoggerAdapter:
    base = logging.getLogger(name if name else __name__)
    return ContextLoggerAdapter(base)


def _create_handler() -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColorConsoleFormatter())
    return handler


def _hook_uvicorn(level: int) -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.propagate = True
        lg.setLevel(level if name != "uvicorn.access" else logging.WARNING)


def configure_logging() -> None:
    if os.name == "nt":
        try:
            import colorama  # type: ignore[reportMissingTypeStubs]

            colorama.init(convert=True, strip=False)
        except Exception:
            pass
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = _create_handler()
    root.addHandler(handler)

    level_name = settings.LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    _hook_uvicorn(level)

    for noisy in [
        "sqlalchemy.engine",
        "asyncpg",
        "alembic",
    ]:
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))


__all__ = ["configure_logging", "get_logger", "ContextLoggerAdapter"]
