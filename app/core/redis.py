from __future__ import annotations

import json
from typing import Any, cast
from collections.abc import Callable, Awaitable

from redis.asyncio import Redis

from app.core.config import settings


_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        from_url = cast(Callable[..., Redis], Redis.from_url)
        _redis = from_url(settings.REDIS_URL, decode_responses=False)
    return _redis


async def publish_json(channel: str, payload: Any) -> None:
    redis = await get_redis()
    publish = cast(Callable[[str, bytes], Awaitable[Any] | Any], redis.publish)
    await publish(channel, json.dumps(payload, ensure_ascii=False).encode("utf-8"))


async def publish_model(channel: str, payload: Any) -> None:
    if hasattr(payload, "model_dump_json"):
        data = cast("Callable[[], str]", payload.model_dump_json)
        raw = data()
    else:
        raw = json.dumps(payload, ensure_ascii=False)
    redis = await get_redis()
    publish = cast(Callable[[str, bytes], Awaitable[Any] | Any], redis.publish)
    await publish(channel, raw.encode("utf-8"))
