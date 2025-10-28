from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import Unauthorized
from app.db.session import get_db
from app.models.user import User
from sqlalchemy import select


security = HTTPBearer(auto_error=False)


DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession, credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> User:
    if credentials is None:
        raise Unauthorized("Could not validate credentials")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        sub = payload.get("sub")
        if sub is None:
            raise Unauthorized("Could not validate credentials")
    except JWTError:
        raise Unauthorized("Invalid token")

    result = await db.execute(select(User).where(User.email == sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise Unauthorized("Could not validate credentials")
    return user
