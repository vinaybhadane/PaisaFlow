"""Database schema, model metadata, and constraint verification tests."""

from decimal import Decimal
import pytest
from sqlalchemy import Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import Base
from backend.app.models.account import Account
from backend.app.models.goal import Goal
from backend.app.models.user import User


def test_metadata_tables_registered() -> None:
    """Verify all 14 documented schema tables are properly registered in metadata."""
    expected_tables = {
        "users",
        "demo_profiles",
        "accounts",
        "categories",
        "merchants",
        "merchant_aliases",
        "transactions",
        "recurring_commitments",
        "recurring_observations",
        "price_change_events",
        "financial_facts",
        "profile_snapshots",
        "goals",
        "scenarios",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_monetary_columns_use_numeric_not_float() -> None:
    """Verify that financial columns strictly use Numeric with precision and scale."""
    tx_table = Base.metadata.tables["transactions"]
    amount_col = tx_table.columns["amount"]
    assert isinstance(amount_col.type, Numeric)
    assert amount_col.type.precision == 18
    assert amount_col.type.scale == 2
    assert amount_col.type.asdecimal is True

    goal_table = Base.metadata.tables["goals"]
    target_col = goal_table.columns["target_amount"]
    assert isinstance(target_col.type, Numeric)
    assert target_col.type.precision == 18
    assert target_col.type.scale == 2

    rc_table = Base.metadata.tables["recurring_commitments"]
    typical_col = rc_table.columns["typical_amount"]
    assert isinstance(typical_col.type, Numeric)


def test_foreign_key_definitions() -> None:
    """Verify documented foreign key constraints between models."""
    tx_table = Base.metadata.tables["transactions"]
    fk_targets = {fk.target_fullname for fk in tx_table.foreign_keys}
    assert "users.id" in fk_targets
    assert "accounts.id" in fk_targets
    assert "merchants.id" in fk_targets
    assert "categories.id" in fk_targets


@pytest.mark.asyncio
async def test_user_account_relationship_and_monetary_decimal(test_db_session: AsyncSession) -> None:
    """Test entity creation and verified Decimal monetary preservation."""
    user = User(
        display_name="Test Verifier",
        email="test.verifier@paisaflow.synthetic",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.flush()

    acct = Account(
        user_id=user.id,
        display_name="Test Checking",
        account_type="checking",
        currency="INR",
    )
    test_db_session.add(acct)
    await test_db_session.flush()

    assert user.id is not None
    assert acct.id is not None
    assert acct.user_id == user.id

    goal = Goal(
        user_id=user.id,
        title="Test Target",
        target_amount=Decimal("15000.50"),
        current_saved_amount=Decimal("5000.25"),
        currency="INR",
        target_date=user.created_at.date(),
        priority="high",
        contribution_frequency="monthly",
    )
    test_db_session.add(goal)
    await test_db_session.flush()

    # Ensure Decimal arithmetic and type preservation
    assert isinstance(goal.target_amount, Decimal)
    assert goal.target_amount == Decimal("15000.50")
    assert goal.current_saved_amount == Decimal("5000.25")
