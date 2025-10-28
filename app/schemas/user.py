from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    name: str | None = None
    phone: str | None = None
    location: str | None = None
    avatar_path: str | None = Field(default=None, exclude=True)
    avatar_url: str | None = Field(default=None)
    intro: str | None = None
    links: list[str] = []
    skills: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }

    def model_post_init(self, __context: Any) -> None:
        if self.avatar_path and not self.avatar_url:
            object.__setattr__(self, "avatar_url", self.avatar_path)


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

    model_config = {"from_attributes": True}
