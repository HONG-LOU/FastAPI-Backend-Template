from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginIn, TokenPair
from app.schemas.user import UserCreate, UserOut


router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: DBSession) -> UserOut:
    exists = await db.execute(select(User).where(User.email == user_in.email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email, hashed_password=get_password_hash(user_in.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, db: DBSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(subject=user.email)
    refresh = create_refresh_token(subject=user.email)

    # 记录刷新令牌 jti
    refresh_row = RefreshToken(
        user_id=user.id,
        jti=refresh["jti"],
        expires_at=datetime.utcfromtimestamp(
            int(jwt_claims(refresh["token"]).get("exp", 0))
        ),
    )
    db.add(refresh_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh["token"])


def jwt_claims(token: str) -> dict:
    # 只解析 payload，不校验签名（用于提取 exp），写在局部帮助函数
    from jose.utils import base64url_decode

    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        payload = parts[1]
        missing_padding = len(payload) % 4
        if missing_padding:
            payload += "=" * (4 - missing_padding)
        import json

        return json.loads(base64url_decode(payload.encode()).decode())
    except Exception:
        return {}


@router.post("/refresh", response_model=TokenPair)
async def refresh(token_pair: TokenPair, db: DBSession) -> TokenPair:
    # 依赖提交 refresh_token，旋转刷新令牌
    from jose import jwt
    from app.core.config import settings

    try:
        payload = jwt.decode(
            token_pair.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # 校验 jti 是否存在且未撤销
    jti = payload.get("jti")
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    row = result.scalar_one_or_none()
    if row is None or row.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )

    # 旋转：撤销旧的，签发新的
    await db.execute(
        update(RefreshToken).where(RefreshToken.id == row.id).values(revoked=True)
    )

    access_token = create_access_token(subject=payload["sub"])
    new_refresh = create_refresh_token(subject=payload["sub"])
    new_row = RefreshToken(
        user_id=row.user_id,
        jti=new_refresh["jti"],
        expires_at=datetime.utcfromtimestamp(
            int(jwt_claims(new_refresh["token"]).get("exp", 0))
        ),
    )
    db.add(new_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=new_refresh["token"])


@router.post("/logout")
async def logout(token_pair: TokenPair, db: DBSession):
    # 撤销当前 refresh
    from jose import jwt
    from app.core.config import settings

    try:
        payload = jwt.decode(
            token_pair.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=400, detail="Malformed token")

    await db.execute(
        update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
    )
    await db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user
