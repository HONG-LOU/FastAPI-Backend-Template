from __future__ import annotations

from datetime import datetime
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, get_current_user
from app.core.redis import publish_json, get_redis
from app.models.chat import ChatParticipant, ChatRoom, Message
from app.models.user import User
from app.schemas.chat import (
    MessageCreate,
    MessageOut,
    RoomCreateDirect,
    RoomOut,
)


router = APIRouter()


@router.post("/rooms/direct", response_model=RoomOut)
async def create_direct_room(
    payload: RoomCreateDirect, db: DBSession, user: User = Depends(get_current_user)
) -> RoomOut:
    # 检查是否已有 direct 房间
    # 简化：按两人唯一房间策略（可扩展为 room_members hash）
    # 这里直接创建一个新房间并插入两名参与者（生产环境可做幂等）
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
    return room


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
    return rows


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
    return msg


# -------- WebSocket (basic) --------


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # 采用 query 参数 token（前端可用 Authorization 头更安全，简化起见）
    await ws.accept()
    try:
        params = dict(ws.query_params)
        room_id = int(params.get("room_id"))
        # 简化：不在 WS 层做用户鉴权（建议前端传 token 并验证）。
        # 订阅 redis 频道并转发消息
        redis = await get_redis()
        pubsub = redis.pubsub()
        channel = f"chat:room:{room_id}"
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
                # 同时也可以从客户端接收 noop/心跳
                # 避免阻塞，使用 receive_text 超时或 try_receive
                # 简化略
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    except WebSocketDisconnect:
        return
