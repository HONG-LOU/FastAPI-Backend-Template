from pydantic import BaseModel, EmailStr, SecretStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: SecretStr


class PendingRegistration(BaseModel):
    email: EmailStr
    hashed_password: str


class RegistrationErrorData(BaseModel):
    field: str | None = Field(default=None)
    reason: str
    hint: str | None = Field(default=None)


class TokenErrorData(BaseModel):
    token_type: str | None = Field(default=None)
    reason: str


class VerificationErrorData(BaseModel):
    reason: str
