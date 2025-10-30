from __future__ import annotations


from fastapi import APIRouter, Depends, Query, WebSocket, UploadFile, File
from fastapi.responses import FileResponse

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
    AttachmentOut,
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
from app.core.config import settings
from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.chat import ChatParticipant, Message
from app.models.attachment import Attachment
from sqlalchemy import and_, select
from pathlib import Path
from datetime import datetime, timezone
import re, uuid, hashlib


router = APIRouter()


@router.get("/rooms", response_model=list[RoomSummaryOut])
async def list_rooms(
    db: DBSession, user: User = Depends(get_current_user)
) -> list[RoomSummaryOut]:
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


# -------- Attachments --------


def _sanitize_filename(name: str) -> str:
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:255] or f"file_{uuid.uuid4().hex}"


def _attachment_url(att_id: int) -> str:
    base = settings.BACKEND_PUBLIC_BASE_URL or ""
    return f"{base}/api/chat/attachments/{att_id}/download"


async def _persist_upload(
    file: UploadFile, root: Path
) -> tuple[str, int, str, str | None]:
    root.mkdir(parents=True, exist_ok=True)
    ext_name = _sanitize_filename(file.filename or "file")
    sub = datetime.now(timezone.utc).strftime("%Y%m/%d")
    d = root / sub
    d.mkdir(parents=True, exist_ok=True)
    key = f"{sub}/{uuid.uuid4().hex}_{ext_name}"
    abs_path = root / key
    hasher = hashlib.sha256()
    size = 0
    with abs_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)
            hasher.update(chunk)
    await file.close()
    return (
        key,
        size,
        file.content_type or "application/octet-stream",
        hasher.hexdigest(),
    )


@router.post("/attachments", response_model=list[AttachmentOut])
async def upload_attachments(
    db: DBSession,
    user: User = Depends(get_current_user),
    files: list[UploadFile] = File(...),
) -> list[AttachmentOut]:
    if not files:
        raise BadRequest("no files")
    root = Path(settings.UPLOAD_DIR)
    items: list[AttachmentOut] = []
    for f in files:
        key, size, ctype, checksum = await _persist_upload(f, root)
        row = Attachment(
            uploader_id=user.id,
            s3_key=key,
            filename=_sanitize_filename(f.filename or "file"),
            content_type=ctype,
            size_bytes=size,
            status="ready",
            checksum=checksum,
        )
        db.add(row)
        await db.flush()
        items.append(
            AttachmentOut(
                id=int(row.id),
                message_id=None,
                filename=row.filename,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
                status=row.status,
                created_at=row.created_at,
                url=_attachment_url(int(row.id)),
            )
        )
    await db.commit()
    return items


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int, db: DBSession, user: User = Depends(get_current_user)
):
    row = (
        await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("attachment not found")
    if row.message_id is not None:
        msg = (
            await db.execute(select(Message).where(Message.id == row.message_id))
        ).scalar_one_or_none()
        if msg is None:
            raise NotFound("message not found for attachment")
        exists = (
            await db.execute(
                select(ChatParticipant).where(
                    and_(
                        ChatParticipant.room_id == msg.room_id,
                        ChatParticipant.user_id == user.id,
                    )
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            raise Forbidden("forbidden")
    else:
        if int(row.uploader_id) != int(user.id):
            raise Forbidden("forbidden")

    path = Path(settings.UPLOAD_DIR) / row.s3_key
    if not path.is_file():
        raise NotFound("file missing")
    return FileResponse(path, media_type=row.content_type, filename=row.filename)
