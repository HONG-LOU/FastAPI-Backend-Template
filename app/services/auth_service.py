from __future__ import annotations

from datetime import datetime, timezone

from jose import jwt
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequest, Conflict, Unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    jwt_claims,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginIn, TokenPair
from app.schemas.user import UserCreate, UserOut


async def register_user(db: AsyncSession, user_in: UserCreate) -> UserOut:
    exists = await db.execute(select(User).where(User.email == user_in.email))
    if exists.scalar_one_or_none() is not None:
        raise Conflict("Email already registered")

    user = User(
        email=user_in.email, hashed_password=get_password_hash(user_in.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


async def login_user(db: AsyncSession, payload: LoginIn) -> TokenPair:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise Unauthorized("Invalid credentials")

    access_token = create_access_token(subject=user.email)
    refresh = create_refresh_token(subject=user.email)

    claims = jwt_claims(refresh["token"])  # 仅解析 exp
    refresh_row = RefreshToken(
        user_id=user.id,
        jti=refresh["jti"],
        expires_at=datetime.fromtimestamp(int(claims.exp or 0), tz=timezone.utc),
    )

    db.add(refresh_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh["token"])


async def rotate_refresh_token(db: AsyncSession, token_pair: TokenPair) -> TokenPair:
    try:
        payload = jwt.decode(
            token_pair.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise Unauthorized("Invalid refresh token")

    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise Unauthorized("Invalid refresh token")

    jti = payload.get("jti")
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    row = result.scalar_one_or_none()
    if row is None or row.revoked:
        raise Unauthorized("Refresh token revoked")

    await db.execute(
        update(RefreshToken).where(RefreshToken.id == row.id).values(revoked=True)
    )

    access_token = create_access_token(subject=payload["sub"])  # type: ignore[index]
    new_refresh = create_refresh_token(subject=payload["sub"])  # type: ignore[index]

    claims = jwt_claims(new_refresh["token"])
    new_row = RefreshToken(
        user_id=row.user_id,
        jti=new_refresh["jti"],
        expires_at=datetime.fromtimestamp(int(claims.exp or 0), tz=timezone.utc),
    )
    db.add(new_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=new_refresh["token"])


async def revoke_refresh_token(
    db: AsyncSession, token_pair: TokenPair
) -> dict[str, bool]:
    try:
        payload = jwt.decode(
            token_pair.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise Unauthorized("Invalid refresh token")

    jti = payload.get("jti")
    if not jti:
        raise BadRequest("Malformed token")

    await db.execute(
        update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
    )
    await db.commit()
    return {"ok": True}
