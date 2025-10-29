from __future__ import annotations

from datetime import datetime, timezone

from jose import jwt
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequest,
    Conflict,
    Unauthorized,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verify_token,
    get_password_hash,
    jwt_claims,
    verify_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginIn, TokenPair, PendingRegistration
from app.schemas.user import UserCreate
from app.services.mailer import send_mail
from app.schemas.common import AckOut
from app.core.redis import get_redis


async def register_user(db: AsyncSession, user_in: UserCreate) -> AckOut:
    exists = await db.execute(select(User).where(User.email == user_in.email))
    if exists.scalar_one_or_none() is not None:
        raise Conflict("Email already registered")

    hashed = get_password_hash(user_in.password)
    token = create_verify_token(subject=user_in.email)
    claims = jwt_claims(token)
    if not claims.jti:
        raise BadRequest("Failed to initiate registration")

    redis = await get_redis()
    key = f"reg:{claims.jti}"
    data = (
        PendingRegistration(email=user_in.email, hashed_password=hashed)
        .model_dump_json()
        .encode()
    )
    ttl = settings.VERIFY_TOKEN_EXPIRE_MINUTES * 60
    await redis.set(key, data, ex=ttl)

    verify_url = f"{settings.BACKEND_PUBLIC_BASE_URL}/api/auth/verify?token={token}"
    html = (
        f"<h3>欢迎注册</h3>"
        f"<p>请点击下方按钮完成邮箱验证：</p>"
        f"<p><a href='{verify_url}' style='padding:10px 16px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px'>验证邮箱</a></p>"
    )
    await send_mail(user_in.email, "注册验证", html)

    return AckOut(ok=True)


async def login_user(db: AsyncSession, payload: LoginIn) -> TokenPair:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise Unauthorized("Invalid credentials")

    access_token = create_access_token(subject=user.email)
    refresh = create_refresh_token(subject=user.email)

    claims = jwt_claims(refresh.token)  # 仅解析 exp
    refresh_row = RefreshToken(
        user_id=user.id,
        jti=refresh.jti,
        expires_at=datetime.fromtimestamp(int(claims.exp or 0), tz=timezone.utc),
    )

    db.add(refresh_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh.token)


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

    claims = jwt_claims(new_refresh.token)
    new_row = RefreshToken(
        user_id=row.user_id,
        jti=new_refresh.jti,
        expires_at=datetime.fromtimestamp(int(claims.exp or 0), tz=timezone.utc),
    )
    db.add(new_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=new_refresh.token)


async def revoke_refresh_token(db: AsyncSession, token_pair: TokenPair) -> AckOut:
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
    return AckOut(ok=True)


async def verify_email_and_issue_tokens(db: AsyncSession, token: str) -> TokenPair:
    try:
        claims = verify_token(token, expected_type="verify")
    except Exception:
        raise Unauthorized("Invalid verification token")

    if not claims.sub:
        raise Unauthorized("Invalid verification token")

    result = await db.execute(select(User).where(User.email == claims.sub))
    user = result.scalar_one_or_none()
    if user is None:
        # lazy create from pending registration
        if not claims.jti:
            raise Unauthorized("Invalid verification token")
        redis = await get_redis()
        key = f"reg:{claims.jti}"
        raw = await redis.get(key)
        if not raw:
            raise Unauthorized("Registration expired or invalid")
        pending = PendingRegistration.model_validate_json(raw)
        if pending.email != claims.sub:
            raise Unauthorized("Invalid registration payload")

        user = User(email=pending.email, hashed_password=pending.hashed_password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        try:
            await redis.delete(key)
        except Exception:
            pass

    if not user.email_verified:
        user.email_verified = True
        await db.commit()

    access_token = create_access_token(subject=user.email)
    refresh = create_refresh_token(subject=user.email)
    rc = jwt_claims(refresh.token)
    row = RefreshToken(
        user_id=user.id,
        jti=refresh.jti,
        expires_at=datetime.fromtimestamp(int(rc.exp or 0), tz=timezone.utc),
    )
    db.add(row)
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh.token)
