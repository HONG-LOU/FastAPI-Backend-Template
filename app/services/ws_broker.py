from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Protocol, cast

from app.core.redis import get_redis
from app.core.metrics import inc, add_gauge
from app.core.logging import get_logger


class WebSocketConnection:
    def __init__(self, ws: Any, *, queue_size: int = 256) -> None:
        import asyncio as _asyncio

        self.ws = ws
        self.queue: _asyncio.Queue[str] = _asyncio.Queue(maxsize=queue_size)
        self._sender_task: _asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._sender_task = loop.create_task(self._sender_loop())

    async def close(self) -> None:
        self._closed = True
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            import contextlib as _contextlib, asyncio as _asyncio

            with _contextlib.suppress(_asyncio.CancelledError):
                await self._sender_task

    async def enqueue(self, payload: str) -> None:
        try:
            self.queue.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                _ = self.queue.get_nowait()
                self.queue.task_done()
            except Exception:
                pass
            inc("ws_queue_drop")
            try:
                self.queue.put_nowait(payload)
            except Exception:
                pass

    async def _sender_loop(self) -> None:
        try:
            while not self._closed:
                payload = await self.queue.get()
                try:
                    await self.ws.send_text(payload)
                finally:
                    self.queue.task_done()
        except Exception:
            pass


class PubSubLike(Protocol):
    def psubscribe(self, *patterns: str | bytes | memoryview) -> Awaitable[Any]: ...

    def punsubscribe(self, *patterns: str | bytes | memoryview) -> Awaitable[Any]: ...

    def get_message(
        self, *, ignore_subscribe_messages: bool = ..., timeout: float | None = ...
    ) -> Awaitable[dict[str, object] | None]: ...

    def close(self) -> Awaitable[Any]: ...


class ChatBroker:
    def __init__(self) -> None:
        self._room_subscribers: dict[int, set[WebSocketConnection]] = {}
        self._pubsub: PubSubLike | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._started = False
        self._logger = get_logger("app.ws")

    async def start(self) -> None:
        if self._started:
            return
        redis = await get_redis()
        pubsub = cast(PubSubLike, cast(Any, redis).pubsub())
        self._pubsub = pubsub
        await pubsub.psubscribe("chat:room:*")
        self._consumer_task = asyncio.create_task(self._consume_loop())
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        try:
            if self._pubsub is not None:
                await self._pubsub.punsubscribe("chat:room:*")
                await self._pubsub.close()
        finally:
            if self._consumer_task and not self._consumer_task.done():
                self._consumer_task.cancel()
                import contextlib as _contextlib, asyncio as _asyncio

                with _contextlib.suppress(_asyncio.CancelledError):
                    await self._consumer_task
            self._started = False

    async def subscribe(self, room_id: int, conn: WebSocketConnection) -> None:
        subs = self._room_subscribers.setdefault(room_id, set())
        subs.add(conn)
        await conn.start()
        inc("ws_subscribe")
        add_gauge("ws_connections", 1)
        self._logger.info(
            "ws subscribed", extra={"room_id": room_id, "subscribers": len(subs)}
        )

    async def unsubscribe(self, room_id: int, conn: WebSocketConnection) -> None:
        subs = self._room_subscribers.get(room_id)
        if subs is not None:
            subs.discard(conn)
            if not subs:
                self._room_subscribers.pop(room_id, None)
        await conn.close()
        inc("ws_unsubscribe")
        add_gauge("ws_connections", -1)
        cnt = len(subs) if subs is not None else 0
        self._logger.info(
            "ws unsubscribed", extra={"room_id": room_id, "subscribers": cnt}
        )

    async def _consume_loop(self) -> None:
        assert self._pubsub is not None
        pubsub = self._pubsub
        try:
            while True:
                message: dict[str, object] | None = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if not message:
                    continue
                mtype_obj = message.get("type")
                if isinstance(mtype_obj, (bytes, bytearray)):
                    mtype = mtype_obj.decode()
                elif mtype_obj is None:
                    mtype = None
                else:
                    mtype = str(mtype_obj)
                if mtype not in {"message", "pmessage"}:
                    continue
                channel_obj = message.get("channel")
                if isinstance(channel_obj, (bytes, bytearray)):
                    ch_str = channel_obj.decode()
                elif channel_obj is None:
                    continue
                else:
                    ch_str = str(channel_obj)
                room_id = self._parse_room_id(ch_str)
                if room_id is None:
                    continue
                data_obj = message.get("data")
                if data_obj is None:
                    continue
                if isinstance(data_obj, (bytes, bytearray)):
                    payload = data_obj.decode()
                else:
                    payload = str(data_obj)
                subs = self._room_subscribers.get(room_id)
                if not subs:
                    continue
                for conn in tuple(subs):
                    await conn.enqueue(payload)
                inc("ws_fanout_messages", len(subs))
                self._logger.info(
                    "ws fanout",
                    extra={"room_id": room_id, "subscribers": len(subs)},
                )
        except Exception:
            pass

    @staticmethod
    def _parse_room_id(channel: str) -> int | None:
        if not channel.startswith("chat:room:"):
            return None
        try:
            return int(channel.split(":")[2])
        except Exception:
            return None


_broker: ChatBroker | None = None


async def get_broker() -> ChatBroker:
    global _broker
    if _broker is None:
        _broker = ChatBroker()
        await _broker.start()
    return _broker
