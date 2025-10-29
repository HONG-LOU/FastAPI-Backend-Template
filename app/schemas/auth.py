from pydantic import BaseModel, EmailStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PendingRegistration(BaseModel):
    email: EmailStr
    hashed_password: str
