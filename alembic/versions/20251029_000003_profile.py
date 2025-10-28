"""profile fields and resume versions

Revision ID: 20251029_000003
Revises: 20251028_000002
Create Date: 2025-10-29 00:00:03.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20251029_000003"
down_revision: str | None = "20251028_000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("name", sa.String(length=127), nullable=True))
        batch.add_column(sa.Column("phone", sa.String(length=31), nullable=True))
        batch.add_column(sa.Column("location", sa.String(length=127), nullable=True))
        batch.add_column(sa.Column("avatar_path", sa.Text(), nullable=True))
        batch.add_column(sa.Column("intro", sa.String(length=500), nullable=True))
        batch.add_column(
            sa.Column(
                "links",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            )
        )
        batch.add_column(
            sa.Column(
                "skills",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            )
        )
    op.create_index(op.f("ix_users_location"), "users", ["location"], unique=False)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_skills_gin ON users USING GIN(skills)"
    )

    with op.batch_alter_table("attachments") as batch:
        batch.alter_column("message_id", existing_type=sa.Integer(), nullable=True)

    op.create_table(
        "user_resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attachment_id"], ["attachments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_resumes_user_id"), "user_resumes", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_resumes_is_current"), "user_resumes", ["is_current"], unique=False
    )
    op.create_index(
        op.f("ix_user_resumes_created_at"), "user_resumes", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_resumes_created_at"), table_name="user_resumes")
    op.drop_index(op.f("ix_user_resumes_is_current"), table_name="user_resumes")
    op.drop_index(op.f("ix_user_resumes_user_id"), table_name="user_resumes")
    op.drop_table("user_resumes")

    with op.batch_alter_table("attachments") as batch:
        batch.alter_column("message_id", existing_type=sa.Integer(), nullable=True)

    op.execute("DROP INDEX IF EXISTS ix_users_skills_gin")
    op.drop_index(op.f("ix_users_location"), table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("skills")
        batch.drop_column("links")
        batch.drop_column("intro")
        batch.drop_column("avatar_path")
        batch.drop_column("location")
        batch.drop_column("phone")
        batch.drop_column("name")
