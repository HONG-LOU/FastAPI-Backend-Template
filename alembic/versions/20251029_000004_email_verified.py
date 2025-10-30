"""email verified

Revision ID: 20251030_000004
Revises: 20251029_000003
Create Date: 2025-10-30 00:00:04.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20251030_000004"
down_revision: str | None = "20251029_000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        op.f("ix_users_email_verified"), "users", ["email_verified"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email_verified"), table_name="users")
    op.drop_column("users", "email_verified")


