from __future__ import annotations

from typing import Any, Awaitable, cast
import asyncio
import contextlib

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import and_, desc, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased
from app.services.ws_broker import get_broker, WebSocketConnection
from app.core.metrics import inc
from app.core.logging import get_logger

from app.core.exceptions import BadRequest, Forbidden
from app.core.redis import get_redis, publish_model
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatParticipant, ChatRoom, Message
from app.models.user import User
from app.schemas.chat import (
    MarkReadIn,
    MessageCreate,
    MessageOut,
    RoomCreateDirect,
    RoomOut,
    UnreadCountOut,
    WSPresence,
    WSChatMessage,
)
from app.schemas.common import AckOut


UNREAD_TTL_SECONDS = 7 * 24 * 3600


def _unread_key(room_id: int, user_id: int) -> str:
    return f"chat:unread:{room_id}:{user_id}"


async def create_direct_room_service(
    db: AsyncSession, payload: RoomCreateDirect, current_user_id: int
) -> RoomOut:
    if payload.user_id == current_user_id:
        raise BadRequest("cannot create direct room with self")

    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)
    stmt = (
        select(ChatRoom)
        .join(cp1, cp1.room_id == ChatRoom.id)
        .join(cp2, cp2.room_id == ChatRoom.id)
        .where(
            and_(
                ChatRoom.type == "direct",
                cp1.user_id == current_user_id,
                cp2.user_id == payload.user_id,
            )
        )
        .order_by(ChatRoom.id)
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing is not None:
        return RoomOut.model_validate(existing, from_attributes=True)

    room = ChatRoom(type="direct")
    db.add(room)
    await db.flush()
    db.add_all(
        [
            ChatParticipant(room_id=room.id, user_id=current_user_id),
            ChatParticipant(room_id=room.id, user_id=payload.user_id),
        ]
    )
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room, from_attributes=True)


async def list_messages_service(
    db: AsyncSession, room_id: int, current_user_id: int, limit: int, cursor: int | None
) -> list[MessageOut]:
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == current_user_id,
            )
        )
    )
    if exists.scalar_one_or_none() is None:
        raise Forbidden("forbidden")

    stmt = select(Message).where(Message.room_id == room_id)
    if cursor is not None:
        stmt = stmt.where(Message.id < cursor)
    stmt = stmt.order_by(desc(Message.id)).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [MessageOut.model_validate(m, from_attributes=True) for m in rows]


async def send_message_service(
    db: AsyncSession, payload: MessageCreate, current_user_id: int
) -> MessageOut:
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(
                ChatParticipant.room_id == payload.room_id,
                ChatParticipant.user_id == current_user_id,
            )
        )
    )
    if exists.scalar_one_or_none() is None:
        raise Forbidden("forbidden")

    msg = Message(
        room_id=payload.room_id,
        sender_id=current_user_id,
        content=payload.content or "",
        kind="text",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    await publish_model(
        f"chat:room:{payload.room_id}",
        WSChatMessage(
            type="message",
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            content=msg.content or "",
            created_at=msg.created_at,
        ),
    )

    redis = await get_redis()
    participants = (
        (
            await db.execute(
                select(ChatParticipant.user_id).where(
                    and_(
                        ChatParticipant.room_id == payload.room_id,
                        ChatParticipant.user_id != current_user_id,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    if participants:
        pipe = redis.pipeline(transaction=False)
        for uid in participants:
            key = _unread_key(payload.room_id, int(uid))
            pipe.set(key, b"0", ex=UNREAD_TTL_SECONDS, nx=True)
            pipe.incr(key)
        try:
            await cast(Awaitable[Any], pipe.execute())
        except Exception:
            pass
    return MessageOut.model_validate(msg, from_attributes=True)


async def mark_read_service(
    db: AsyncSession, room_id: int, body: MarkReadIn, current_user_id: int
) -> AckOut:
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == current_user_id,
            )
        )
    )
    row = exists.scalar_one_or_none()
    if row is None:
        raise Forbidden("forbidden")

    await db.execute(
        update(ChatParticipant)
        .where(
            and_(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == current_user_id,
                or_(
                    ChatParticipant.last_read_message_id.is_(None),
                    ChatParticipant.last_read_message_id < body.last_read_message_id,
                ),
            )
        )
        .values(last_read_message_id=body.last_read_message_id)
    )
    await db.commit()

    await publish_model(
        f"chat:room:{room_id}",
        WSPresence(
            type="message_read",
            room_id=room_id,
            user_id=current_user_id,
            status=str(body.last_read_message_id),
        ),
    )
    try:
        redis = await get_redis()
        await cast(
            Awaitable[Any],
            redis.set(
                _unread_key(room_id, current_user_id), b"0", ex=UNREAD_TTL_SECONDS
            ),
        )
    except Exception:
        pass
    return AckOut(ok=True)


async def unread_count_service(
    db: AsyncSession, room_id: int, current_user_id: int
) -> UnreadCountOut:
    try:
        redis = await get_redis()
        val = await cast(
            Awaitable[Any], redis.get(_unread_key(room_id, current_user_id))
        )
        if val is not None:
            try:
                return UnreadCountOut(count=int(val))
            except Exception:
                pass
    except Exception:
        pass

    result = await db.execute(
        select(ChatParticipant).where(
            and_(
                ChatParticipant.room_id == room_id,
                ChatParticipant.user_id == current_user_id,
            )
        )
    )
    me = result.scalar_one_or_none()
    if me is None:
        raise Forbidden("forbidden")

    last_read = me.last_read_message_id or 0

    from sqlalchemy import func as sa_func

    cnt = (
        await db.execute(
            select(sa_func.count()).where(
                and_(
                    Message.room_id == room_id,
                    Message.id > last_read,
                    Message.sender_id != current_user_id,
                )
            )
        )
    ).scalar_one()

    try:
        redis = await get_redis()
        await cast(
            Awaitable[Any],
            redis.set(
                _unread_key(room_id, current_user_id),
                str(int(cnt)).encode(),
                ex=UNREAD_TTL_SECONDS,
            ),
        )
    except Exception:
        pass
    return UnreadCountOut(count=int(cnt))


async def ws_authorize_and_room_check(
    token: str | None,
    room_id: int,
    db_factory: async_sessionmaker[AsyncSession],
) -> User | None:
    """为 WS 鉴权与权限校验提供服务函数，返回用户对象或 None。"""
    from jose import JWTError, jwt  # 局部导入避免依赖循环
    from app.core.config import settings
    from sqlalchemy import select
    from app.models.chat import ChatParticipant

    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")
        if not sub:
            return None
    except JWTError:
        return None

    async with db_factory() as db:
        result = await db.execute(select(User).where(User.email == sub))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        exists = await db.execute(
            select(ChatParticipant).where(
                and_(
                    ChatParticipant.room_id == room_id,
                    ChatParticipant.user_id == user.id,
                )
            )
        )
        if exists.scalar_one_or_none() is None:
            return None
        return user


async def ws_handler(ws: WebSocket) -> None:
    """WebSocket 处理：鉴权、presence、订阅转发。路由层仅转发请求。"""
    params = dict(ws.query_params)
    token = params.get("token")
    if not token:
        auth_header = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]

    room_id_raw = params.get("room_id")
    if room_id_raw is None:
        await ws.close(code=1008)
        return
    try:
        room_id = int(room_id_raw)
    except Exception:
        await ws.close(code=1008)
        return

    user: User | None = await ws_authorize_and_room_check(
        token, room_id, AsyncSessionLocal
    )
    if user is None:
        await ws.close(code=1008)
        return

    await ws.accept()
    logger = get_logger("app.ws")
    logger.info("ws connected", extra={"room_id": room_id, "user_id": user.id})

    redis = await get_redis()
    broker = await get_broker()
    channel = f"chat:room:{room_id}"
    presence_key = f"chat:room:{room_id}:presence:{user.id}"

    async def _heartbeat_task() -> None:
        try:
            while True:
                await cast(Awaitable[Any], redis.set(presence_key, b"1", ex=30))
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            return
        except Exception:
            pass

    hb_task = asyncio.create_task(_heartbeat_task())
    await publish_model(
        channel,
        WSPresence(type="presence", room_id=room_id, user_id=user.id, status="online"),
    )
    inc("ws_presence_online")

    conn = WebSocketConnection(ws)
    await broker.subscribe(room_id, conn)
    try:
        last = 0.0
        tokens = 5.0
        rate = 5.0
        cap = 10.0
        while True:
            try:
                _ = await ws.receive_text()
                now = asyncio.get_event_loop().time()
                if last:
                    tokens = min(cap, tokens + (now - last) * rate)
                last = now
                if tokens < 1.0:
                    await asyncio.sleep(0.1)
                    continue
                tokens -= 1.0
            except WebSocketDisconnect:
                break
            except Exception:
                await asyncio.sleep(0.05)
    finally:
        try:
            hb_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await hb_task
            await broker.unsubscribe(room_id, conn)
            await cast(Awaitable[Any], redis.delete(presence_key))
            await publish_model(
                channel,
                WSPresence(
                    type="presence", room_id=room_id, user_id=user.id, status="offline"
                ),
            )
            inc("ws_presence_offline")
            logger.info(
                "ws disconnected", extra={"room_id": room_id, "user_id": user.id}
            )
        except Exception:
            pass
