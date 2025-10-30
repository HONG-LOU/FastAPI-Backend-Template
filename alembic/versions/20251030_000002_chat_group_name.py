"""add chat_rooms.name for groups

Revision ID: 20251030_000002
Revises: 20251024_000001
Create Date: 2025-10-30 00:00:02

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251030_000002"
down_revision: str | None = "20251030_000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_rooms", sa.Column("name", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_chat_rooms_name"), "chat_rooms", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_rooms_name"), table_name="chat_rooms")
    op.drop_column("chat_rooms", "name")


