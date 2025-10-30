from __future__ import annotations

from typing import Any, Awaitable, cast
import asyncio
import contextlib

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import and_, desc, select, update, or_, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased
from app.services.ws_broker import get_broker, WebSocketConnection
from app.core.metrics import inc
from app.core.logging import get_logger

from app.core.exceptions import BadRequest, Forbidden, UserNotFound, NotFound
from app.core.redis import get_redis, publish_model
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatParticipant, ChatRoom, Message
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.chat import (
    MarkReadIn,
    MessageCreate,
    MessageOut,
    PeerOut,
    RoomSummaryOut,
    RoomCreateDirect,
    RoomCreateGroup,
    ParticipantsChangeIn,
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
    target_user_id: int
    if payload.email is not None:
        user_row = (
            await db.execute(select(User).where(User.email == payload.email))
        ).scalar_one_or_none()
        if user_row is None:
            raise UserNotFound("User not found by email")
        target_user_id = int(user_row.id)
    else:
        target_user_id = int(payload.user_id or 0)
        user_row = (
            await db.execute(select(User).where(User.id == target_user_id))
        ).scalar_one_or_none()
        if user_row is None:
            raise UserNotFound("User not found by id")
    if target_user_id == current_user_id:
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
                cp2.user_id == target_user_id,
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
            ChatParticipant(room_id=room.id, user_id=target_user_id),
        ]
    )
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room, from_attributes=True)


def _att_url(att_id: int) -> str:
    return f"/api/chat/attachments/{att_id}/download"


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
    mids = [int(m.id) for m in rows]
    amap: dict[int, list[Attachment]] = {}
    if mids:
        arows = (
            await db.execute(select(Attachment).where(Attachment.message_id.in_(mids)))
        ).scalars().all()
        for a in arows:
            amap.setdefault(int(a.message_id or 0), []).append(a)
    out: list[MessageOut] = []
    for m in rows:
        atts = [
            {
                "id": int(a.id),
                "message_id": int(m.id),
                "filename": a.filename,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "status": a.status,
                "created_at": a.created_at,
                "url": _att_url(int(a.id)),
            }
            for a in amap.get(int(m.id), [])
        ]
        mo = MessageOut(
            id=int(m.id),
            room_id=int(m.room_id),
            sender_id=int(m.sender_id),
            kind=m.kind,
            content=m.content,
            created_at=m.created_at,
            attachments=atts,
        )
        out.append(mo)
    return out


async def list_rooms_service(
    db: AsyncSession, current_user_id: int
) -> list[RoomSummaryOut]:
    cp_self = ChatParticipant
    last_sub = (
        select(Message.room_id, func.max(Message.id).label("last_id"))
        .group_by(Message.room_id)
        .subquery()
    )

    base = (
        select(ChatRoom, Message)
        .join(cp_self, cp_self.room_id == ChatRoom.id)
        .outerjoin(last_sub, last_sub.c.room_id == ChatRoom.id)
        .outerjoin(Message, Message.id == last_sub.c.last_id)
        .where(cp_self.user_id == current_user_id)
        .order_by(Message.id.desc().nullslast(), ChatRoom.id.desc())
    )

    rows = (await db.execute(base)).all()
    room_ids = [int(r[0].id) for r in rows]

    peers_map: dict[int, tuple[int, str | None, str, str | None]] = {}
    if room_ids:
        cp2 = ChatParticipant
        peer_stmt = (
            select(cp2.room_id, User.id, User.name, User.email, User.avatar_path)
            .join(User, User.id == cp2.user_id)
            .where(and_(cp2.room_id.in_(room_ids), cp2.user_id != current_user_id))
        )
        for room_id, uid, name, email, avatar_path in (
            await db.execute(peer_stmt)
        ).all():
            peers_map[int(room_id)] = (int(uid), name, email, avatar_path)

    redis = await get_redis()
    unread: dict[int, int] = {}
    if room_ids:
        pipe = redis.pipeline(transaction=False)
        for room_id in room_ids:
            pipe.get(_unread_key(room_id, current_user_id))
        vals = await pipe.execute()  # type: ignore
        for room_id, v in zip(room_ids, vals):
            try:
                unread[room_id] = int(v or 0)
            except Exception:
                unread[room_id] = 0

    items: list[RoomSummaryOut] = []
    for room, last in rows:
        peer = peers_map.get(int(room.id))
        peer_out = (
            None
            if peer is None
            else PeerOut(id=peer[0], name=peer[1], email=peer[2], avatar_url=peer[3])
        )
        last_out = (
            None
            if last is None
            else MessageOut.model_validate(last, from_attributes=True)
        )
        items.append(
            RoomSummaryOut(
                id=int(room.id),
                type=room.type,
                name=getattr(room, "name", None),
                peer=peer_out,
                last_message=last_out,
                unread_count=unread.get(int(room.id), 0),
                created_at=room.created_at,
            )
        )
    return items


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

    att_ids = [int(x) for x in (payload.attachment_ids or [])]
    if att_ids:
        arows = (
            await db.execute(
                select(Attachment).where(
                    and_(Attachment.id.in_(att_ids), Attachment.uploader_id == current_user_id)
                )
            )
        ).scalars().all()
        if len(arows) != len(att_ids):
            raise Forbidden("invalid attachment owner or missing")
        if any(a.message_id is not None for a in arows):
            raise BadRequest("attachment already linked")

    msg = Message(
        room_id=payload.room_id,
        sender_id=current_user_id,
        content=payload.content or "",
        kind="file" if att_ids else "text",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    if att_ids:
        await db.execute(
            update(Attachment)
            .where(Attachment.id.in_(att_ids))
            .values(message_id=msg.id)
        )
        await db.commit()
        arows = (
            await db.execute(select(Attachment).where(Attachment.message_id == msg.id))
        ).scalars().all()
    else:
        arows = []

    await publish_model(
        f"chat:room:{payload.room_id}",
        WSChatMessage(
            type="message",
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            content=msg.content or None,
            created_at=msg.created_at,
            attachments=[
                {
                    "id": int(a.id),
                    "message_id": int(msg.id),
                    "filename": a.filename,
                    "content_type": a.content_type,
                    "size_bytes": a.size_bytes,
                    "status": a.status,
                    "created_at": a.created_at,
                    "url": _att_url(int(a.id)),
                }
                for a in arows
            ],
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
    return MessageOut(
        id=int(msg.id),
        room_id=int(msg.room_id),
        sender_id=int(msg.sender_id),
        kind=msg.kind,
        content=msg.content or None,
        created_at=msg.created_at,
        attachments=[
            {
                "id": int(a.id),
                "message_id": int(msg.id),
                "filename": a.filename,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "status": a.status,
                "created_at": a.created_at,
                "url": _att_url(int(a.id)),
            }
            for a in arows
        ],
    )


async def create_group_room_service(
    db: AsyncSession, payload: RoomCreateGroup, current_user_id: int
) -> RoomOut:
    target_ids: set[int] = set()
    if payload.user_ids:
        target_ids.update(int(x) for x in payload.user_ids if int(x) != current_user_id)
    if payload.emails:
        rows = (
            await db.execute(select(User.id).where(User.email.in_(payload.emails)))
        ).scalars().all()
        target_ids.update(int(x) for x in rows if int(x) != current_user_id)
    if not target_ids:
        raise BadRequest("no valid participants")

    room = ChatRoom(type="group", name=(payload.name or None))
    db.add(room)
    await db.flush()

    values = [
        {"room_id": room.id, "user_id": current_user_id},
        *({"room_id": room.id, "user_id": uid} for uid in sorted(target_ids)),
    ]
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(ChatParticipant).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ChatParticipant.room_id.key, ChatParticipant.user_id.key])
    await db.execute(stmt)
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room, from_attributes=True)


async def add_participants_service(
    db: AsyncSession, room_id: int, payload: ParticipantsChangeIn, current_user_id: int
) -> AckOut:
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == current_user_id)
        )
    )
    if exists.scalar_one_or_none() is None:
        raise Forbidden("forbidden")

    target_ids: set[int] = set(payload.user_ids or [])
    if payload.emails:
        rows = (
            await db.execute(select(User.id).where(User.email.in_(payload.emails)))
        ).scalars().all()
        target_ids.update(int(x) for x in rows)
    if not target_ids:
        raise BadRequest("no valid participants")

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(ChatParticipant).values(
        [{"room_id": room_id, "user_id": int(uid)} for uid in sorted(target_ids)]
    ).on_conflict_do_nothing(index_elements=[ChatParticipant.room_id.key, ChatParticipant.user_id.key])
    await db.execute(stmt)
    await db.commit()
    return AckOut(ok=True)


async def remove_participants_service(
    db: AsyncSession, room_id: int, payload: ParticipantsChangeIn, current_user_id: int
) -> AckOut:
    exists = await db.execute(
        select(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id == current_user_id)
        )
    )
    if exists.scalar_one_or_none() is None:
        raise Forbidden("forbidden")

    ids: set[int] = set(payload.user_ids or [])
    if payload.emails:
        rows = (
            await db.execute(select(User.id).where(User.email.in_(payload.emails)))
        ).scalars().all()
        ids.update(int(x) for x in rows)
    if not ids:
        raise BadRequest("no valid participants")

    from sqlalchemy import delete

    await db.execute(
        delete(ChatParticipant).where(
            and_(ChatParticipant.room_id == room_id, ChatParticipant.user_id.in_(ids))
        )
    )
    await db.commit()
    return AckOut(ok=True)


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


async def list_all_users_service(
    db: AsyncSession, current_user_id: int, query: str | None, limit: int
) -> list[PeerOut]:
    q = select(User).where(User.is_active.is_(True), User.id != current_user_id)
    if query:
        like = f"%{query.strip()}%"
        q = q.where(or_(User.name.ilike(like), User.email.ilike(like)))
    q = q.order_by(User.name.nullslast(), User.email).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [PeerOut(id=int(u.id), email=u.email, name=u.name, avatar_url=u.avatar_path) for u in rows]


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
