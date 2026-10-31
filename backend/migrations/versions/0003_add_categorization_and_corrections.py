"""0003 add categorization_rules and transaction_corrections tables

Revision ID: 0003_add_categorization_and_corrections
Revises: 0002_add_import_batches
Create Date: 2026-10-31 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_add_categorization_and_corrections"
down_revision: Union[str, None] = "0002_add_import_batches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. categorization_rules table
    op.create_table(
        "categorization_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subcategory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("source_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_categorization_rules_user_id", "categorization_rules", ["user_id"])
    op.create_index("ix_categorization_rules_category_id", "categorization_rules", ["category_id"])
    op.create_index("ix_categorization_rules_user_priority", "categorization_rules", ["user_id", "priority"])
    op.create_index("ix_categorization_rules_user_active", "categorization_rules", ["user_id", "is_active"])

    # 2. transaction_corrections table
    op.create_table(
        "transaction_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categorization_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_transaction_corrections_user_id", "transaction_corrections", ["user_id"])
    op.create_index("ix_transaction_corrections_transaction_id", "transaction_corrections", ["transaction_id"])
    op.create_index("ix_transaction_corrections_user_created", "transaction_corrections", ["user_id", "created_at"])
    op.create_index("ix_transaction_corrections_tx_field", "transaction_corrections", ["transaction_id", "field_name"])


def downgrade() -> None:
    op.drop_table("transaction_corrections")
    op.drop_table("categorization_rules")

