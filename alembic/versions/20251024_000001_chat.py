"""chat tables

Revision ID: 20251024_000001
Revises: 20251023_000000
Create Date: 2025-10-24 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251024_000001"
down_revision: Union[str, None] = "20251023_000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_rooms_type"), "chat_rooms", ["type"], unique=False)
    op.create_index(
        op.f("ix_chat_rooms_created_at"), "chat_rooms", ["created_at"], unique=False
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=True, server_default="text"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_room_id"), "messages", ["room_id"], unique=False)
    op.create_index(
        op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False
    )
    op.create_index(op.f("ix_messages_kind"), "messages", ["kind"], unique=False)
    op.create_index(
        op.f("ix_messages_created_at"), "messages", ["created_at"], unique=False
    )

    op.create_table(
        "chat_participants",
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.String(length=16), nullable=True, server_default="participant"
        ),
        sa.Column(
            "joined_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.Column("last_read_message_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_id", "user_id"),
    )
    op.create_index(
        op.f("ix_chat_participants_user_id"),
        "chat_participants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_participants_last_read_message_id"),
        "chat_participants",
        ["last_read_message_id"],
        unique=False,
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("uploader_id", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=127), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=True, server_default="pending"
        ),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_attachments_created_at"), "attachments", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_attachments_status"), "attachments", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_attachments_message_id"), "attachments", ["message_id"], unique=False
    )
    op.create_index(
        op.f("ix_attachments_uploader_id"), "attachments", ["uploader_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_attachments_uploader_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_message_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_status"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_created_at"), table_name="attachments")
    op.drop_table("attachments")

    op.drop_index(op.f("ix_chat_participants_user_id"), table_name="chat_participants")
    op.drop_table("chat_participants")

    op.drop_index(op.f("ix_messages_created_at"), table_name="messages")
    op.drop_index(op.f("ix_messages_kind"), table_name="messages")
    op.drop_index(op.f("ix_messages_sender_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_room_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_chat_rooms_created_at"), table_name="chat_rooms")
    op.drop_index(op.f("ix_chat_rooms_type"), table_name="chat_rooms")
    op.drop_table("chat_rooms")
