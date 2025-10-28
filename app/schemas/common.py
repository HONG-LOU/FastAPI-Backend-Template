from __future__ import annotations

from typing import Mapping

from pydantic import BaseModel


class AckOut(BaseModel):
    ok: bool


class MetricsOut(BaseModel):
    counters: Mapping[str, int]
    gauges: Mapping[str, float]
