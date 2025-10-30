from __future__ import annotations


from fastapi import APIRouter, Depends, Query, WebSocket

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.common import AckOut
from app.schemas.chat import (
    MarkReadIn,
    MessageCreate,
    MessageOut,
    RoomSummaryOut,
    RoomCreateDirect,
    RoomOut,
    UnreadCountOut,
    RoomCreateGroup,
    ParticipantsChangeIn,
    PeerOut,
)
from app.services.chat_service import (
    create_direct_room_service,
    list_rooms_service,
    list_messages_service,
    mark_read_service,
    send_message_service,
    unread_count_service,
    ws_handler,
    create_group_room_service,
    add_participants_service,
    remove_participants_service,
    list_all_users_service,
)


router = APIRouter()
@router.get("/rooms", response_model=list[RoomSummaryOut])
async def list_rooms(db: DBSession, user: User = Depends(get_current_user)) -> list[RoomSummaryOut]:
    return await list_rooms_service(db, user.id)


@router.get("/users", response_model=list[PeerOut])
async def list_all_users(
    db: DBSession,
    user: User = Depends(get_current_user),
    query: str | None = Query(None, description="按姓名或邮箱模糊搜索"),
    limit: int = Query(200, ge=1, le=1000),
) -> list[PeerOut]:
    return await list_all_users_service(db, user.id, query, limit)


@router.post("/rooms/direct", response_model=RoomOut)
async def create_direct_room(
    payload: RoomCreateDirect, db: DBSession, user: User = Depends(get_current_user)
) -> RoomOut:
    return await create_direct_room_service(db, payload, user.id)


@router.post("/rooms/group", response_model=RoomOut)
async def create_group_room(
    payload: RoomCreateGroup, db: DBSession, user: User = Depends(get_current_user)
) -> RoomOut:
    return await create_group_room_service(db, payload, user.id)


@router.post("/rooms/{room_id}/participants", response_model=AckOut)
async def add_participants(
    room_id: int,
    payload: ParticipantsChangeIn,
    db: DBSession,
    user: User = Depends(get_current_user),
) -> AckOut:
    return await add_participants_service(db, room_id, payload, user.id)


@router.delete("/rooms/{room_id}/participants", response_model=AckOut)
async def remove_participants(
    room_id: int,
    payload: ParticipantsChangeIn,
    db: DBSession,
    user: User = Depends(get_current_user),
) -> AckOut:
    return await remove_participants_service(db, room_id, payload, user.id)


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
