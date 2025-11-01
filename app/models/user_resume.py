from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import DateTimeMixin


class UserResume(Base, DateTimeMixin):
    __tablename__ = "user_resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attachment_id: Mapped[int] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
