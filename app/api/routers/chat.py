from __future__ import annotations


from fastapi import APIRouter, Depends, Query, WebSocket

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.common import AckOut
from app.schemas.chat import (
    MarkReadIn,
    MessageCreate,
    MessageOut,
    RoomCreateDirect,
    RoomOut,
    UnreadCountOut,
)
from app.services.chat_service import (
    create_direct_room_service,
    list_messages_service,
    mark_read_service,
    send_message_service,
    unread_count_service,
    ws_handler,
)


router = APIRouter()


@router.post("/rooms/direct", response_model=RoomOut)
async def create_direct_room(
    payload: RoomCreateDirect, db: DBSession, user: User = Depends(get_current_user)
) -> RoomOut:
    return await create_direct_room_service(db, payload, user.id)


@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
async def list_messages(
    room_id: int,
    db: DBSession,
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    cursor: int | None = Query(None, description="cursor for pagination"),
) -> list[MessageOut]:
    return await list_messages_service(db, room_id, user.id, limit, cursor)


@router.post("/messages", response_model=MessageOut)
async def send_message(
    payload: MessageCreate, db: DBSession, user: User = Depends(get_current_user)
) -> MessageOut:
    return await send_message_service(db, payload, user.id)


@router.post("/rooms/{room_id}/read", response_model=AckOut)
async def mark_read(
    room_id: int,
    body: MarkReadIn,
    db: DBSession,
    user: User = Depends(get_current_user),
) -> AckOut:
    return await mark_read_service(db, room_id, body, user.id)


@router.get("/rooms/{room_id}/unread_count", response_model=UnreadCountOut)
async def unread_count(
    room_id: int, db: DBSession, user: User = Depends(get_current_user)
) -> UnreadCountOut:
    return await unread_count_service(db, room_id, user.id)


# -------- WebSocket (basic) --------


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_handler(ws)
