from __future__ import annotations

from typing import Any


_counters: dict[str, int] = {}
_gauges: dict[str, float] = {}


def inc(name: str, amount: int = 1) -> None:
    _counters[name] = _counters.get(name, 0) + int(amount)


def set_gauge(name: str, value: float) -> None:
    _gauges[name] = float(value)


def add_gauge(name: str, delta: float) -> None:
    _gauges[name] = _gauges.get(name, 0.0) + float(delta)


def snapshot() -> dict[str, Any]:
    return {"counters": dict(_counters), "gauges": dict(_gauges)}
