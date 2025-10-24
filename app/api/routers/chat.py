from __future__ import annotations

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import aliased

from app.api.deps import DBSession, get_current_user
from app.core.redis import publish_json, get_redis
from app.models.chat import ChatParticipant, ChatRoom, Message
from app.models.user import User
from app.schemas.chat import (
    MessageCreate,
    MessageOut,
    RoomCreateDirect,
    RoomOut,
    MarkReadIn,
    UnreadCountOut,
)
from jose import JWTError, jwt
from app.core.config import settings
from app.db.session import AsyncSessionLocal


router = APIRouter()


@router.post("/rooms/direct", response_model=RoomOut)
async def create_direct_room(
    payload: RoomCreateDirect, db: DBSession, user: User = Depends(get_current_user)
) -> RoomOut:
    # 自聊校验
    if payload.user_id == user.id:
        raise HTTPException(
            status_code=400, detail="cannot create direct room with self"
        )

    # 若两人已有 direct 房间则复用
    cp1 = aliased(ChatParticipant)
    cp2 = aliased(ChatParticipant)
    stmt = (
        select(ChatRoom)
        .join(cp1, cp1.room_id == ChatRoom.id)
        .join(cp2, cp2.room_id == ChatRoom.id)
        .where(
            and_(
                ChatRoom.type == "direct",
                cp1.user_id == user.id,
                cp2.user_id == payload.user_id,
            )
        )
        .order_by(ChatRoom.id)
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing is not None:
        return RoomOut.model_validate(existing, from_attributes=True)

    # 不存在则创建
    room = ChatRoom(type="direct")
    db.add(room)
    await db.flush()
    db.add_all(
        [
            ChatParticipant(room_id=room.id, user_id=user.id),
            ChatParticipant(room_id=room.id, user_id=payload.user_id),
        ]
    )
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room, from_attributes=True)


@router.get("/rooms/{room_id}/messages", response_model=List[MessageOut])
async def list_messages(
    room_id: int,
    db: DBSession,
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    cursor: int | None = Query(None, description="基于 id 的倒序分页游标"),
) -> List[MessageOut]:
    # 校验参与者
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == user.id)
        )
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="forbidden")

    stmt = select(Message).where(Message.room_id == room_id)
    if cursor is not None:
        stmt = stmt.where(Message.id < cursor)
    stmt = stmt.order_by(desc(Message.id)).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [MessageOut.model_validate(m, from_attributes=True) for m in rows]


@router.post("/messages", response_model=MessageOut)
async def send_message(
    payload: MessageCreate, db: DBSession, user: User = Depends(get_current_user)
) -> MessageOut:
    # 校验参与者
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(
                ChatParticipant.room_id == payload.room_id,
                ChatParticipant.user_id == user.id,
            )
        )
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="forbidden")

    msg = Message(
        room_id=payload.room_id,
        sender_id=user.id,
        content=payload.content or "",
        kind="text",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # 广播到 redis 频道
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


@router.post("/rooms/{room_id}/read")
async def mark_read(
    room_id: int,
    body: MarkReadIn,
    db: DBSession,
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    # 校验参与者
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == user.id)
        )
    )
    row = exists.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=403, detail="forbidden")

    # 仅向前更新 last_read_message_id
    await db.execute((select(ChatParticipant)))  # type: ignore[call-overload]
    # 使用简单方式：直接发原生 SQL 更新避免引入 ORM 实例状态
    from sqlalchemy import text

    await db.execute(
        text(
            """
            update chat_participants
            set last_read_message_id = :mid
            where room_id = :rid and user_id = :uid and (last_read_message_id is null or last_read_message_id < :mid)
            """
        ),
        {"mid": body.last_read_message_id, "rid": room_id, "uid": user.id},
    )
    await db.commit()

    # 通知同房间成员已读（可选）
    await publish_json(
        f"chat:room:{room_id}",
        {
            "type": "message_read",
            "room_id": room_id,
            "user_id": user.id,
            "last_read_message_id": body.last_read_message_id,
        },
    )
    return {"ok": True}


@router.get("/rooms/{room_id}/unread_count", response_model=UnreadCountOut)
async def unread_count(
    room_id: int, db: DBSession, user: User = Depends(get_current_user)
) -> UnreadCountOut:
    # 校验参与者并取 last_read_message_id
    result = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == user.id)
        )
    )
    me = result.scalar_one_or_none()
    if me is None:
        raise HTTPException(status_code=403, detail="forbidden")

    last_read = me.last_read_message_id or 0

    # 计算未读：本房间且消息 id 大于 last_read，且发送者不等于自己
    from sqlalchemy import func as sa_func

    cnt = (
        await db.execute(
            select(sa_func.count()).where(
                and_(
                    Message.room_id == room_id,
                    Message.id > last_read,
                    Message.sender_id != user.id,
                )
            )
        )
    ).scalar_one()
    return UnreadCountOut(count=int(cnt))


# -------- WebSocket (basic) --------


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # WebSocket 鉴权：从 query 参数 token 或 Authorization 头中提取 access token
    params = dict(ws.query_params)
    token = params.get("token")
    if not token:
        auth_header = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]

    # 需要房间 ID
    room_id_raw = params.get("room_id")
    if room_id_raw is None:
        await ws.close(code=1008)
        return
    try:
        room_id = int(room_id_raw)
    except Exception:
        await ws.close(code=1008)
        return

    # 校验 token 并加载用户
    user = None
    try:
        if not token:
            raise JWTError("missing token")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")
        if not sub:
            raise JWTError("invalid sub")
    except JWTError:
        await ws.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == sub))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            await ws.close(code=1008)
            return

        # 房间成员校验
        exists = await db.execute(
            select(ChatParticipant).where(
                and_(
                    ChatParticipant.room_id == room_id,
                    ChatParticipant.user_id == user.id,
                )
            )
        )
        if exists.scalar_one_or_none() is None:
            await ws.close(code=1008)
            return

    # 通过鉴权与权限检查后再接受连接
    await ws.accept()

    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = f"chat:room:{room_id}"

    # 记录在线状态并广播 presence:online
    online_set = f"chat:room:{room_id}:online"
    try:
        await redis.sadd(online_set, str(user.id))
        await publish_json(
            channel,
            {
                "type": "presence",
                "room_id": room_id,
                "user_id": user.id,
                "status": "online",
            },
        )

        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, (bytes, bytearray)):
                        await ws.send_bytes(data)
                    else:
                        await ws.send_json(data)
                # 可在此接收客户端心跳/指令（略）
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    except WebSocketDisconnect:
        pass
    finally:
        # 清理在线状态并广播 presence:offline
        try:
            await redis.srem(online_set, str(user.id))
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
            pass
