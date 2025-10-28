from fastapi import APIRouter, Depends

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn, TokenPair
from app.schemas.user import UserCreate, UserOut
from app.services.auth_service import (
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: DBSession) -> UserOut:
    return await register_user(db, user_in)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, db: DBSession) -> TokenPair:
    return await login_user(db, payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(token_pair: TokenPair, db: DBSession) -> TokenPair:
    return await rotate_refresh_token(db, token_pair)


@router.post("/logout")
async def logout(token_pair: TokenPair, db: DBSession):
    return await revoke_refresh_token(db, token_pair)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
