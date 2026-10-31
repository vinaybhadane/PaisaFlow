"""Tests for the synthetic demo data pipeline, idempotency, and reset safety."""

from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.account import Account
from backend.app.models.goal import Goal
from backend.app.models.recurring_commitment import PriceChangeEvent
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.services.demo_data_service import DemoDataService


@pytest.mark.asyncio
async def test_demo_seeding_creates_both_personas(test_db_session: AsyncSession) -> None:
    """Verify that both Asha Mehta and Kabir Shah are created with accounts and goals."""
    service = DemoDataService(seed=42)
    summary = await service.seed_all(test_db_session)

    assert len(summary["personas_seeded"]) == 2
    assert "Asha Mehta (Demo)" in summary["personas_seeded"]
    assert "Kabir Shah (Demo)" in summary["personas_seeded"]

    # Verify Asha Mehta records
    asha_stmt = select(User).where(User.email == "asha.mehta.demo@paisaflow.synthetic")
    asha = (await test_db_session.execute(asha_stmt)).scalar_one_or_none()
    assert asha is not None

    # Verify Accounts
    acct_stmt = select(Account).where(Account.user_id == asha.id)
    accounts = (await test_db_session.execute(acct_stmt)).scalars().all()
    assert len(accounts) == 2

    # Verify Goals
    goal_stmt = select(Goal).where(Goal.user_id == asha.id)
    goal = (await test_db_session.execute(goal_stmt)).scalar_one_or_none()
    assert goal is not None
    assert goal.title == "Emergency Fund"
    assert goal.target_amount == Decimal("50000.00")
    assert goal.current_saved_amount == Decimal("21000.00")


@pytest.mark.asyncio
async def test_documented_edge_cases_in_synthetic_data(test_db_session: AsyncSession) -> None:
    """Verify documented edge cases: price changes, transfers, refunds, duplicates."""
    service = DemoDataService(seed=42)
    await service.seed_all(test_db_session)

    asha_stmt = select(User).where(User.email == "asha.mehta.demo@paisaflow.synthetic")
    asha = (await test_db_session.execute(asha_stmt)).scalar_one()

    # 1. Price Change Event
    pce_stmt = select(PriceChangeEvent)
    pce = (await test_db_session.execute(pce_stmt)).scalar_one_or_none()
    assert pce is not None
    assert pce.previous_amount == Decimal("149.00")
    assert pce.new_amount == Decimal("179.00")
    assert pce.absolute_change == Decimal("30.00")

    # 2. Own-Account Transfer
    transfer_stmt = select(Transaction).where(
        Transaction.user_id == asha.id,
        Transaction.transaction_type == "transfer",
    )
    transfers = (await test_db_session.execute(transfer_stmt)).scalars().all()
    assert len(transfers) == 2  # Debit + Credit pair
    assert all(tx.is_excluded is True for tx in transfers)

    # 3. Refund
    refund_stmt = select(Transaction).where(
        Transaction.user_id == asha.id,
        Transaction.transaction_type == "refund",
    )
    refund = (await test_db_session.execute(refund_stmt)).scalar_one_or_none()
    assert refund is not None
    assert refund.direction == "credit"
    assert refund.amount == Decimal("850.00")

    # 4. Duplicate Transaction
    dup_stmt = select(Transaction).where(
        Transaction.user_id == asha.id,
        Transaction.review_status == "flagged",
    )
    dup = (await test_db_session.execute(dup_stmt)).scalar_one_or_none()
    assert dup is not None
    assert dup.duplicate_fingerprint is not None


@pytest.mark.asyncio
async def test_seeding_is_idempotent(test_db_session: AsyncSession) -> None:
    """Verify that calling seed multiple times does not duplicate users or transactions."""
    service = DemoDataService(seed=42)
    await service.seed_all(test_db_session)

    # Count initial users
    count_stmt = select(User)
    initial_users = len((await test_db_session.execute(count_stmt)).scalars().all())

    # Run seed again
    await service.seed_all(test_db_session)
    final_users = len((await test_db_session.execute(count_stmt)).scalars().all())

    assert initial_users == final_users == 2


@pytest.mark.asyncio
async def test_reset_affects_only_synthetic_demo_records(test_db_session: AsyncSession) -> None:
    """Verify reset script deletes synthetic records while preserving non-synthetic ones."""
    # Create non-synthetic user
    real_user = User(
        display_name="Real Test User",
        email="real.user@example.com",
    )
    test_db_session.add(real_user)
    await test_db_session.commit()

    # Seed synthetic personas
    service = DemoDataService(seed=42)
    await service.seed_all(test_db_session)

    # Perform reset
    reset_result = await service.reset_synthetic_demo_data(test_db_session)
    assert reset_result["deleted_users"] == 2

    # Verify real user is preserved
    stmt = select(User).where(User.id == real_user.id)
    surviving_user = (await test_db_session.execute(stmt)).scalar_one_or_none()
    assert surviving_user is not None
    assert surviving_user.email == "real.user@example.com"
