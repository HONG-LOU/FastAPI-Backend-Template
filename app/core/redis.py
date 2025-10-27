from __future__ import annotations

import json
from typing import Any, Optional, Callable, Awaitable, cast

from redis.asyncio import Redis

from app.core.config import settings


_redis: Optional[Redis] = None


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
