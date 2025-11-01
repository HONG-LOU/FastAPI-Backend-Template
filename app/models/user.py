from datetime import datetime

from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import DateTimeMixin


class User(Base, DateTimeMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    name: Mapped[str | None] = mapped_column(String(127))
    phone: Mapped[str | None] = mapped_column(String(31))
    location: Mapped[str | None] = mapped_column(String(127), index=True)
    avatar_path: Mapped[str | None] = mapped_column(Text)
    intro: Mapped[str | None] = mapped_column(String(500))
    links: Mapped[list[str]] = mapped_column(JSONB, default=list)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, index=True)
