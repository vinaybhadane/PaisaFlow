"""0001 Initial database schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-31 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=32), server_default="en-IN", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("default_currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. demo_profiles
    op.create_table(
        "demo_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_key", sa.String(length=64), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("profile_label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_demo_profiles_user_id", "demo_profiles", ["user_id"])
    op.create_index("ix_demo_profiles_persona_key", "demo_profiles", ["persona_key"])

    # 3. accounts
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("demo_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("demo_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_demo_profile_id", "accounts", ["demo_profile_id"])

    # 4. categories
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category_type", sa.String(length=32), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )

    # 5. merchants
    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_fictional_demo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_merchants_canonical_name", "merchants", ["canonical_name"], unique=True)

    # 6. merchant_aliases
    op.create_table(
        "merchant_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_pattern", sa.String(length=255), nullable=False),
        sa.Column("match_type", sa.String(length=32), server_default="exact", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_merchant_aliases_merchant_id", "merchant_aliases", ["merchant_id"])
    op.create_index("ix_merchant_aliases_alias_pattern", "merchant_aliases", ["alias_pattern"])

    # 7. transactions
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subcategory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("categorization_method", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.String(length=32), nullable=True),
        sa.Column("review_status", sa.String(length=32), server_default="confirmed", nullable=False),
        sa.Column("duplicate_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("is_excluded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_transactions_amount_non_negative"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_import_batch_id", "transactions", ["import_batch_id"])
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_duplicate_fingerprint", "transactions", ["duplicate_fingerprint"])
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "transaction_date"])
    op.create_index("ix_transactions_user_cat_date", "transactions", ["user_id", "category_id", "transaction_date"])
    op.create_index("ix_transactions_user_merch_date", "transactions", ["user_id", "merchant_id", "transaction_date"])
    op.create_index("ix_transactions_user_fingerprint", "transactions", ["user_id", "duplicate_fingerprint"])

    # 8. recurring_commitments
    op.create_table(
        "recurring_commitments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("cadence", sa.String(length=32), nullable=False),
        sa.Column("estimated_cadence_days", sa.Integer(), nullable=True),
        sa.Column("typical_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("min_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("max_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("confidence", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="likely", nullable=False),
        sa.Column("last_observed_date", sa.Date(), nullable=True),
        sa.Column("next_expected_date", sa.Date(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recurring_commitments_user_id", "recurring_commitments", ["user_id"])
    op.create_index("ix_recurring_commitments_user_status", "recurring_commitments", ["user_id", "status"])

    # 9. recurring_observations
    op.create_table(
        "recurring_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recurring_commitments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recurring_observations_commitment_id", "recurring_observations", ["commitment_id"])
    op.create_index("ix_recurring_observations_transaction_id", "recurring_observations", ["transaction_id"])

    # 10. price_change_events
    op.create_table(
        "price_change_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recurring_commitments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("new_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("absolute_change", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("percentage_change", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="possible", nullable=False),
    )
    op.create_index("ix_price_change_events_commitment_id", "price_change_events", ["commitment_id"])

    # 11. financial_facts
    op.create_table(
        "financial_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(length=32), nullable=True),
        sa.Column("source_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_financial_facts_user_id", "financial_facts", ["user_id"])
    op.create_index("ix_financial_facts_effective_from", "financial_facts", ["effective_from"])
    op.create_index("ix_financial_facts_user_type_from", "financial_facts", ["user_id", "fact_type", "effective_from"])

    # 12. profile_snapshots
    op.create_table(
        "profile_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("income_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("expense_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("net_cash_flow", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("fixed_cost_estimate", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("variable_cost_estimate", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("data_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_profile_snapshots_user_id", "profile_snapshots", ["user_id"])

    # 13. goals
    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("current_saved_amount", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("contribution_frequency", sa.String(length=16), server_default="monthly", nullable=False),
        sa.Column("planned_contribution", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_amount > 0", name="ck_goals_target_amount_positive"),
        sa.CheckConstraint("current_saved_amount >= 0", name="ck_goals_saved_amount_non_negative"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_user_status", "goals", ["user_id", "status"])

    # 14. scenarios
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("scenario_type", sa.String(length=64), nullable=False),
        sa.Column("input_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("baseline_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scenario_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculation_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scenarios_user_id", "scenarios", ["user_id"])


def downgrade() -> None:
    op.drop_table("scenarios")
    op.drop_table("goals")
    op.drop_table("profile_snapshots")
    op.drop_table("financial_facts")
    op.drop_table("price_change_events")
    op.drop_table("recurring_observations")
    op.drop_table("recurring_commitments")
    op.drop_table("transactions")
    op.drop_table("merchant_aliases")
    op.drop_table("merchants")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("demo_profiles")
    op.drop_table("users")

