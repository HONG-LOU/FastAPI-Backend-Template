from __future__ import annotations

import json
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import settings


_redis: Optional[Redis] = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis


async def publish_json(channel: str, payload: Any) -> None:
    redis = await get_redis()
    await redis.publish(
        channel, json.dumps(payload, ensure_ascii=False).encode("utf-8")
    )
