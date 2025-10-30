from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy import select, update, String, or_
from sqlalchemy.dialects.postgresql import array as pg_array, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequest, Conflict, NotFound
from app.models.attachment import Attachment
from app.models.user import User
from app.models.user_resume import UserResume
from app.schemas.user import ResumeVersionOut, UserOut, UserUpdate


def _uploads_dir() -> Path:
    base = getattr(settings, "UPLOAD_DIR", "uploads")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    (p / "avatars").mkdir(parents=True, exist_ok=True)
    (p / "resumes").mkdir(parents=True, exist_ok=True)
    return p


async def get_me_service(db: AsyncSession, user_id: int) -> UserOut:
    row = await db.get(User, user_id)
    if row is None:
        raise NotFound("User not found")

    resume_row = (
        await db.execute(
            select(
                UserResume.id,
                UserResume.created_at,
                Attachment.id,
                Attachment.filename,
                Attachment.size_bytes,
                Attachment.s3_key,
            )
            .join(Attachment, Attachment.id == UserResume.attachment_id)
            .where(
                UserResume.user_id == user_id, UserResume.is_current == True
            )  # noqa: E712
            .limit(1)
        )
    ).one_or_none()

    base = UserOut.model_validate(row, from_attributes=True)
    if resume_row:
        rid, created_at, aid, fname, size, path = resume_row
        resume = ResumeVersionOut(
            id=rid,
            attachment_id=aid,
            filename=str(fname),
            size_bytes=int(size),
            created_at=created_at,
            path=str(path),
        )
        return base.model_copy(update={"resume": resume})
    return base


async def update_me_service(
    db: AsyncSession,
    user_id: int,
    payload: UserUpdate,
    *,
    force: bool,
    if_updated_at: datetime | None,
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFound()
    if (
        if_updated_at
        and not force
        and user.updated_at.replace(microsecond=0)
        != if_updated_at.replace(microsecond=0)
    ):
        raise Conflict("Profile changed, confirm to overwrite")

    if payload.email and payload.email != user.email:
        exists = await db.execute(select(User.id).where(User.email == payload.email))
        if exists.scalar_one_or_none() is not None:
            raise Conflict("Email already in use")

    for field in ("name", "email", "phone", "location", "intro", "links", "skills"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


def _validate_avatar(file: UploadFile) -> None:
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise BadRequest("Avatar must be JPEG or PNG")


async def upload_avatar_service(
    db: AsyncSession, user_id: int, file: UploadFile
) -> UserOut:
    _validate_avatar(file)
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise BadRequest("Avatar size must be <= 2MB")

    suffix = ".jpg" if file.content_type == "image/jpeg" else ".png"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dest = _uploads_dir() / "avatars" / f"{user_id}_{ts}{suffix}"
    dest.write_bytes(data)

    user = await db.get(User, user_id)
    if user is None:
        raise NotFound()
    user.avatar_path = str(dest.as_posix())
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


async def upload_resume_service(
    db: AsyncSession, user_id: int, file: UploadFile
) -> ResumeVersionOut:
    data = await file.read()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_name = Path(file.filename or f"resume_{ts}").name
    dest = _uploads_dir() / "resumes" / f"{user_id}_{ts}_{safe_name}"
    dest.write_bytes(data)

    attach = Attachment(
        message_id=None,
        uploader_id=user_id,
        s3_key=str(dest.as_posix()),
        filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        status="ready",
        checksum=None,
    )
    db.add(attach)
    await db.flush()

    await db.execute(
        update(UserResume)
        .where(
            UserResume.user_id == user_id, UserResume.is_current == True
        )  # noqa: E712
        .values(is_current=False)
    )

    ur = UserResume(user_id=user_id, attachment_id=attach.id, is_current=True)
    db.add(ur)
    await db.commit()
    await db.refresh(ur)
    return ResumeVersionOut(
        id=ur.id,
        attachment_id=attach.id,
        filename=attach.filename,
        size_bytes=attach.size_bytes,
        created_at=ur.created_at,
        path=attach.s3_key,
    )


async def list_resume_versions_service(
    db: AsyncSession, user_id: int
) -> list[ResumeVersionOut]:
    q = (
        select(
            UserResume.id,
            UserResume.created_at,
            Attachment.id,
            Attachment.filename,
            Attachment.size_bytes,
            Attachment.s3_key,
        )
        .join(Attachment, Attachment.id == UserResume.attachment_id)
        .where(UserResume.user_id == user_id)
        .order_by(UserResume.created_at.desc())
    )
    rows = (await db.execute(q)).all()
    out: list[ResumeVersionOut] = []
    for rid, created_at, aid, fname, size, path in rows:
        out.append(
            ResumeVersionOut(
                id=rid,
                attachment_id=aid,
                filename=str(fname),
                size_bytes=int(size),
                created_at=created_at,
                path=str(path),
            )
        )
    return out


async def search_by_skills_service(
    db: AsyncSession, skills: Iterable[str], limit: int
) -> list[UserOut]:
    skills = [s.strip() for s in skills if s and s.strip()]
    if not skills:
        return []
    param = pg_array(skills, type_=ARRAY(String()))
    q = select(User).where(User.skills.overlap(param)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [UserOut.model_validate(u, from_attributes=True) for u in rows]


async def list_users_service(
    db: AsyncSession, *, q: str | None, limit: int, cursor: int | None
) -> list[UserOut]:
    stmt = select(User)
    if q:
        kw = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(kw), User.name.ilike(kw)))
    if cursor is not None:
        stmt = stmt.where(User.id < cursor)
    stmt = stmt.order_by(User.id.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [UserOut.model_validate(u, from_attributes=True) for u in rows]
