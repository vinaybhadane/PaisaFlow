"""0004 add coach_conversations and coach_messages tables

Revision ID: 0004_add_coach_conversations
Revises: 0003_add_categorization_and_corrections
Create Date: 2026-10-31 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_add_coach_conversations"
down_revision: Union[str, None] = "0003_add_categorization_and_corrections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. coach_conversations table
    op.create_table(
        "coach_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="Financial Consultation", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_coach_conversations_user_id", "coach_conversations", ["user_id"])
    op.create_index("ix_coach_conversations_user_updated", "coach_conversations", ["user_id", "updated_at"])

    # 2. coach_messages table
    op.create_table(
        "coach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coach_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("grounded_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_coach_messages_conversation_id", "coach_messages", ["conversation_id"])
    op.create_index("ix_coach_messages_conv_created", "coach_messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_coach_messages_conv_created", table_name="coach_messages")
    op.drop_index("ix_coach_messages_conversation_id", table_name="coach_messages")
    op.drop_table("coach_messages")

    op.drop_index("ix_coach_conversations_user_updated", table_name="coach_conversations")
    op.drop_index("ix_coach_conversations_user_id", table_name="coach_conversations")
    op.drop_table("coach_conversations")

