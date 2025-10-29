from __future__ import annotations

from datetime import datetime
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    computed_field,
    ConfigDict,
    SecretStr,
)


class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    email_verified: bool
    name: str | None = None
    phone: str | None = None
    location: str | None = None
    avatar_path: str | None = Field(default=None, exclude=True)
    intro: str | None = None
    links: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resume: "ResumeVersionOut | None" = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[misc]
    @property
    def avatar_url(self) -> str | None:
        return self.avatar_path


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=127)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=31)
    location: str | None = Field(None, max_length=127)
    intro: str | None = Field(None, max_length=500)
    links: list[str] | None = None
    skills: list[str] | None = None

    @field_validator("skills")
    @classmethod
    def dedup_skills(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return sorted(set(s.strip() for s in v if s and s.strip()))


class ResumeVersionOut(BaseModel):
    id: int
    attachment_id: int
    filename: str
    size_bytes: int
    created_at: datetime
    path: str

    model_config = ConfigDict(from_attributes=True)
