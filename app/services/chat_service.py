from __future__ import annotations

from typing import Any, Awaitable, cast

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import and_, desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased
from redis.asyncio.client import PubSub

from app.core.exceptions import BadRequest, Forbidden
from app.core.redis import get_redis, publish_json
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
)


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

    await publish_json(
        f"chat:room:{payload.room_id}",
        {
            "type": "message",
            "id": msg.id,
            "room_id": msg.room_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        },
    )
    return MessageOut.model_validate(msg, from_attributes=True)


async def mark_read_service(
    db: AsyncSession, room_id: int, body: MarkReadIn, current_user_id: int
) -> dict[str, bool]:
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
        text(
            """
            update chat_participants
            set last_read_message_id = :mid
            where room_id = :rid and user_id = :uid and (last_read_message_id is null or last_read_message_id < :mid)
            """
        ),
        {"mid": body.last_read_message_id, "rid": room_id, "uid": current_user_id},
    )
    await db.commit()

    await publish_json(
        f"chat:room:{room_id}",
        {
            "type": "message_read",
            "room_id": room_id,
            "user_id": current_user_id,
            "last_read_message_id": body.last_read_message_id,
        },
    )
    return {"ok": True}


async def unread_count_service(
    db: AsyncSession, room_id: int, current_user_id: int
) -> UnreadCountOut:
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

    redis = await get_redis()
    pubsub: PubSub = redis.pubsub()
    channel = f"chat:room:{room_id}"
    online_set = f"chat:room:{room_id}:online"

    try:
        await cast(Awaitable[Any], redis.sadd(online_set, str(user.id)))
        await publish_json(
            channel,
            {
                "type": "presence",
                "room_id": room_id,
                "user_id": user.id,
                "status": "online",
            },
        )

        await cast(Awaitable[Any], pubsub.subscribe(channel))
        try:
            while True:
                message = await cast(
                    Awaitable[dict[str, Any] | None],
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                )
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, (bytes, bytearray)):
                        await ws.send_bytes(bytes(data))
                    else:
                        await ws.send_json(data)
        finally:
            await cast(Awaitable[Any], pubsub.unsubscribe(channel))
            await cast(Awaitable[Any], pubsub.close())
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await cast(Awaitable[Any], redis.srem(online_set, str(user.id)))
            await publish_json(
                channel,
                {
                    "type": "presence",
                    "room_id": room_id,
                    "user_id": user.id,
                    "status": "offline",
                },
            )
        except Exception:
            # 忽略清理阶段的异常
            pass
