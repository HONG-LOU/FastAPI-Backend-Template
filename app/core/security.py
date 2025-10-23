from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_jwt_token(
    subject: str,
    token_type: str,
    expires_minutes: int,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    jti = uuid4().hex
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": settings.APP_NAME,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"token": token, "jti": jti}


def create_access_token(
    subject: str, extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    return _create_jwt_token(
        subject=subject,
        token_type="access",
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        extra_claims=extra_claims,
    )["token"]


def create_refresh_token(subject: str) -> Dict[str, str]:
    # 返回 token 与 jti，便于与数据库记录关联
    return _create_jwt_token(
        subject=subject,
        token_type="refresh",
        expires_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
    )
