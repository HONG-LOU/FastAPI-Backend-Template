from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.user import ResumeVersionOut, UserOut, UserUpdate
from app.services.profile_service import (
    get_me_service,
    list_resume_versions_service,
    search_by_skills_service,
    update_me_service,
    upload_avatar_service,
    upload_resume_service,
)


router = APIRouter()


@router.get("/me", response_model=UserOut)
async def me(db: DBSession, user: User = Depends(get_current_user)) -> UserOut:
    return await get_me_service(db, user.id)


@router.put("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    db: DBSession,
    user: User = Depends(get_current_user),
    confirm: bool = Query(False, description="是否确认覆盖修改"),
    if_updated_at: datetime | None = Query(
        None, description="并发控制，传入客户端持有的更新时间"
    ),
) -> UserOut:
    return await update_me_service(
        db, user.id, payload, force=confirm, if_updated_at=if_updated_at
    )


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    db: DBSession,
    user: User = Depends(get_current_user),
    file: UploadFile = File(..., description="JPEG/PNG <= 2MB"),
) -> UserOut:
    return await upload_avatar_service(db, user.id, file)


@router.post("/me/resume", response_model=ResumeVersionOut)
async def upload_resume(
    db: DBSession,
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
) -> ResumeVersionOut:
    return await upload_resume_service(db, user.id, file)


@router.get("/me/resume/versions", response_model=list[ResumeVersionOut])
async def list_resume_versions(
    db: DBSession, user: User = Depends(get_current_user)
) -> list[ResumeVersionOut]:
    return await list_resume_versions_service(db, user.id)


@router.get("/search", response_model=list[UserOut])
async def search_users(
    db: DBSession,
    skills: list[str] = Query(
        ..., description="技能标签，如 ?skills=python&skills=react"
    ),
    limit: int = Query(50, ge=1, le=200),
) -> list[UserOut]:
    return await search_by_skills_service(db, skills, limit)
