from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn, TokenPair
from app.schemas.common import AckOut
from app.schemas.user import UserCreate, UserOut
from app.services.profile_service import get_me_service
from app.services.auth_service import (
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_email_and_issue_tokens,
)


router = APIRouter()


@router.post("/register", response_model=AckOut)
async def register(user_in: UserCreate, db: DBSession) -> AckOut:
    return await register_user(db, user_in)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, db: DBSession) -> TokenPair:
    return await login_user(db, payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(token_pair: TokenPair, db: DBSession) -> TokenPair:
    return await rotate_refresh_token(db, token_pair)


@router.post("/logout", response_model=AckOut)
async def logout(token_pair: TokenPair, db: DBSession) -> AckOut:
    return await revoke_refresh_token(db, token_pair)


@router.get("/me", response_model=UserOut)
async def me(db: DBSession, current_user: User = Depends(get_current_user)) -> UserOut:
    return await get_me_service(db, current_user.id)


@router.get("/verify")
async def verify(token: str, db: DBSession) -> Response:
    tokens = await verify_email_and_issue_tokens(db, token)
    from app.core.config import settings

    url = (
        f"{settings.FRONTEND_BASE_URL}/?access_token={tokens.access_token}"
        f"&refresh_token={tokens.refresh_token}&token_type={tokens.token_type}"
    )
    return RedirectResponse(url)
