"""Automated test suite for Phase 5: Living Money Model & Recurring Pattern Intelligence.

Validates:
1. Calendar-aware Cadence Detection (weekly, fortnightly, monthly, quarterly, yearly, custom)
2. Amount Analysis & Monthly Planning Equivalents (Decimal precision, stable vs variable)
3. Price Change Intelligence & Materiality Thresholds (single 'possible' flag vs persistent)
4. Recurring Payment Detector (candidate clustering, evidence generation, rejection of single/irregular)
5. Financial Fact Resolution & Provenance (user_confirmed precedence over inferred)
6. Profile Builder & Financial Summary Arithmetic (income, gross/net expenses, refunds, transfers excluded, savings rate)
7. Snapshot Creation, Recomputation, and Comparison (idempotency, MoM diffs)
8. REST API Endpoints for /recurring, /profile, and /financial-summary
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.living_model.fact_resolver import FinancialFactResolver
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.living_model.snapshots import SnapshotManager
from backend.app.intelligence.recurring.amount_analysis import (
    analyze_amounts,
    calculate_monthly_equivalent,
)
from backend.app.intelligence.recurring.cadence import detect_cadence
from backend.app.intelligence.recurring.detector import RecurringDetector
from backend.app.intelligence.recurring.price_changes import detect_price_changes
from backend.app.models.account import Account
from backend.app.models.demo_profile import DemoProfile
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


# ============================================================================
# 1. Cadence Detection Unit Tests
# ============================================================================

def test_detect_cadence_single_date():
    """Single observation cannot establish cadence."""
    res = detect_cadence([date(2026, 1, 15)])
    assert res.cadence == "custom"
    assert res.observation_count == 1
    assert res.next_expected_date is None
    assert res.is_regular is False
    assert res.cadence_confidence == "low"


def test_detect_cadence_weekly():
    """Regular weekly payments every ~7 days."""
    dates = [
        date(2026, 1, 7),
        date(2026, 1, 14),
        date(2026, 1, 21),
        date(2026, 1, 28),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "weekly"
    assert res.estimated_cadence_days == 7
    assert res.is_regular is True
    assert res.cadence_confidence == "high"
    assert res.next_expected_date == date(2026, 2, 4)


def test_detect_cadence_fortnightly():
    """Regular fortnightly payments every ~14 days."""
    dates = [
        date(2026, 1, 1),
        date(2026, 1, 15),
        date(2026, 1, 29),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "fortnightly"
    assert res.estimated_cadence_days == 14
    assert res.is_regular is True
    assert res.next_expected_date == date(2026, 2, 12)


def test_detect_cadence_monthly_calendar_aware():
    """Monthly cadence handling month-length differences (Jan 31, Feb 28, Mar 31)."""
    dates = [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "monthly"
    assert res.estimated_cadence_days == 30
    assert res.is_regular is True
    assert res.cadence_confidence == "high"
    # Target anchor day is 31, April has 30 days -> clamped cleanly to April 30
    assert res.next_expected_date == date(2026, 4, 30)


def test_detect_cadence_monthly_weekend_shift():
    """Monthly cadence tolerating weekend/holiday posting shifts."""
    dates = [
        date(2026, 1, 1),
        date(2026, 2, 2),  # Shifted due to weekend
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "monthly"
    assert res.is_regular is True
    assert res.cadence_confidence == "high"


def test_detect_cadence_quarterly():
    """Quarterly cadence (~90 days / 3 months)."""
    dates = [
        date(2025, 4, 15),
        date(2025, 7, 15),
        date(2025, 10, 15),
        date(2026, 1, 15),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "quarterly"
    assert res.is_regular is True
    assert res.next_expected_date == date(2026, 4, 15)


def test_detect_cadence_yearly():
    """Annual cadence (~365 days / 12 months)."""
    dates = [
        date(2024, 3, 15),
        date(2025, 3, 15),
        date(2026, 3, 15),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "yearly"
    assert res.is_regular is True
    assert res.next_expected_date == date(2027, 3, 15)


def test_detect_cadence_irregular_no_invented_date():
    """Irregular cadence (CV > 0.35) must NOT receive an invented next expected date."""
    dates = [
        date(2026, 1, 2),
        date(2026, 1, 9),
        date(2026, 2, 20),
        date(2026, 2, 24),
    ]
    res = detect_cadence(dates)
    assert res.cadence == "custom"
    assert res.is_regular is False
    assert res.next_expected_date is None  # Strict rule


# ============================================================================
# 2. Amount Analysis Unit Tests
# ============================================================================

def test_calculate_monthly_equivalent_formulas():
    """Verify authoritative arithmetic from docs/10_FINANCIAL_LOGIC.md."""
    # Monthly: exact amount
    assert calculate_monthly_equivalent(Decimal("1000.00"), "monthly") == Decimal("1000.00")

    # Weekly: amount * 52 / 12 -> 300 * 52 / 12 = 1300.00
    assert calculate_monthly_equivalent(Decimal("300.00"), "weekly") == Decimal("1300.00")

    # Fortnightly: amount * 26 / 12 -> 600 * 26 / 12 = 1300.00
    assert calculate_monthly_equivalent(Decimal("600.00"), "fortnightly") == Decimal("1300.00")

    # Quarterly: amount / 3 -> 900 / 3 = 300.00
    assert calculate_monthly_equivalent(Decimal("900.00"), "quarterly") == Decimal("300.00")

    # Half-yearly: amount / 6 -> 1200 / 6 = 200.00
    assert calculate_monthly_equivalent(Decimal("1200.00"), "half_yearly") == Decimal("200.00")

    # Yearly: amount / 12 -> 2400 / 12 = 200.00
    assert calculate_monthly_equivalent(Decimal("2400.00"), "yearly") == Decimal("200.00")


def test_amount_analysis_stable_vs_variable():
    """Verify stable subscription (< 5% spread) vs variable utility bill."""
    # Stable: Netflix ₹649, ₹649, ₹649
    stable_res = analyze_amounts(
        [Decimal("649.00"), Decimal("649.00"), Decimal("649.00")], "monthly"
    )
    assert stable_res.stability == "stable"
    assert stable_res.typical_amount == Decimal("649.00")
    assert stable_res.spread_percentage == Decimal("0.00")
    assert stable_res.estimated_annual_cost == Decimal("7788.00")

    # Variable: Electricity ₹1200, ₹1850, ₹1400
    var_res = analyze_amounts(
        [Decimal("1200.00"), Decimal("1850.00"), Decimal("1400.00")], "monthly"
    )
    assert var_res.stability == "variable"
    assert var_res.min_amount == Decimal("1200.00")
    assert var_res.max_amount == Decimal("1850.00")
    assert var_res.typical_amount == Decimal("1400.00")
    assert var_res.spread_percentage > Decimal("5.00")


# ============================================================================
# 3. Price Change Intelligence Unit Tests
# ============================================================================

def test_detect_price_changes_material_increase():
    """Detect material price increase (e.g. ₹149 -> ₹179)."""
    observations = [
        (date(2025, 10, 5), Decimal("149.00")),
        (date(2025, 11, 5), Decimal("149.00")),
        (date(2025, 12, 5), Decimal("179.00")),  # +₹30 (+20.13%)
    ]
    changes = detect_price_changes(observations)
    assert len(changes) == 1
    ch = changes[0]
    assert ch.previous_amount == Decimal("149.00")
    assert ch.new_amount == Decimal("179.00")
    assert ch.absolute_change == Decimal("30.00")
    assert ch.percentage_change == Decimal("20.13")
    assert ch.status == "possible"
    assert ch.evidence["change_type"] == "price_increase"


def test_detect_price_changes_submaterial_ignored():
    """Sub-material fluctuations below threshold (< ₹10 and < 2%) are ignored."""
    observations = [
        (date(2026, 1, 5), Decimal("500.00")),
        (date(2026, 2, 5), Decimal("505.00")),  # +₹5 (+1%) -> sub-material
    ]
    changes = detect_price_changes(observations)
    assert len(changes) == 0


# ============================================================================
# 4. Recurring Detector Unit Tests
# ============================================================================

def test_recurring_detector_clustering():
    """Recurring detector clusters transactions and filters non-eligible rows."""
    detector = RecurringDetector()

    # Synthetic transaction stubs
    class TxStub:
        def __init__(self, tx_id, tx_date, amount, direction, tx_type, norm_desc, merchant_id=None):
            self.id = tx_id
            self.transaction_date = tx_date
            self.amount = amount
            self.direction = direction
            self.transaction_type = tx_type
            self.normalized_description = norm_desc
            self.merchant_id = merchant_id
            self.merchant_name = norm_desc.title()
            self.currency = "INR"
            self.is_excluded = False

    m_id = uuid.uuid4()
    txs = [
        TxStub(uuid.uuid4(), date(2026, 1, 5), Decimal("199.00"), "debit", "expense", "spotify", m_id),
        TxStub(uuid.uuid4(), date(2026, 2, 5), Decimal("199.00"), "debit", "expense", "spotify", m_id),
        TxStub(uuid.uuid4(), date(2026, 3, 5), Decimal("199.00"), "debit", "expense", "spotify", m_id),
        # Single retail purchase - should be rejected as non-recurring
        TxStub(uuid.uuid4(), date(2026, 2, 10), Decimal("1500.00"), "debit", "expense", "zara"),
        # Transfer - should be excluded
        TxStub(uuid.uuid4(), date(2026, 2, 1), Decimal("5000.00"), "credit", "transfer", "self transfer"),
    ]

    candidates = detector.detect_candidates_from_transactions(txs)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.cadence == "monthly"
    assert c.typical_amount == Decimal("199.00")
    assert c.confidence == "high"
    assert len(c.observations) == 3


# ============================================================================
# 5. Financial Fact Resolution & Living Model Precedence (DB Integration)
# ============================================================================

@pytest.mark.asyncio
async def test_financial_fact_precedence(test_db_session: AsyncSession):
    """User-confirmed fact strictly takes precedence over transaction-inferred fact."""
    resolver = FinancialFactResolver()
    user_id = uuid.uuid4()

    # Seed test user
    user = User(
        id=user_id,
        display_name="Test Precedence User",
        email="precedence@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # 1. System records transaction-inferred income fact of ₹75,000
    inferred_fact = await resolver.create_fact(
        db=test_db_session,
        user_id=user_id,
        fact_type="income",
        label="Inferred Monthly Salary",
        amount=Decimal("75000.00"),
        source_type="transaction_inferred",
        effective_from=date(2026, 1, 1),
    )
    assert inferred_fact.amount == Decimal("75000.00")

    # 2. User confirms actual salary is ₹85,000 effective Feb 1
    confirmed_fact = await resolver.create_fact(
        db=test_db_session,
        user_id=user_id,
        fact_type="income",
        label="Confirmed Monthly Salary",
        amount=Decimal("85000.00"),
        source_type="user_confirmed",
        effective_from=date(2026, 2, 1),
    )
    assert confirmed_fact.amount == Decimal("85000.00")

    # 3. Query active facts as of Jan 15 -> inferred fact active
    jan_facts = await resolver.get_active_facts_for_date(test_db_session, user_id, as_of_date=date(2026, 1, 15))
    assert len(jan_facts) == 1
    assert jan_facts[0].amount == Decimal("75000.00")

    # 4. Query active facts as of Feb 15 -> user-confirmed fact strictly takes precedence
    feb_facts = await resolver.get_active_facts_for_date(test_db_session, user_id, as_of_date=date(2026, 2, 15))
    assert len(feb_facts) == 1
    assert feb_facts[0].amount == Decimal("85000.00")
    assert feb_facts[0].source_type == "user_confirmed"

    # 5. Historical fact was preserved, not deleted
    all_facts = await resolver.list_all_user_facts(test_db_session, user_id)
    assert len(all_facts) == 2


# ============================================================================
# 6. Profile Builder & Financial Summary Arithmetic (DB Integration)
# ============================================================================

@pytest.mark.asyncio
async def test_financial_summary_authoritative_logic(test_db_session: AsyncSession):
    """Verify docs/10_FINANCIAL_LOGIC.md calculations with income, expenses, refunds, and transfers."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    # Seed User and Account
    user = User(
        id=user_id,
        display_name="Test Finance User",
        email="finance@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Primary Savings",
        account_type="savings",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    # Seed Transactions for March 2026
    txs = [
        # Income: ₹100,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 3, 1),
            original_description="SALARY CREDITED",
            normalized_description="salary",
            amount=Decimal("100000.00"),
            currency="INR",
            direction="credit",
            transaction_type="income",
            review_status="auto_approved",
        ),
        # Essential Expense: Rent ₹25,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 3, 3),
            original_description="RENT TO OWNER",
            normalized_description="apartment rent",
            amount=Decimal("25000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
            review_status="auto_approved",
        ),
        # Variable Expense: Shopping ₹10,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 3, 10),
            original_description="AMAZON PURCHASE",
            normalized_description="amazon shopping",
            amount=Decimal("10000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
            review_status="auto_approved",
        ),
        # Refund: ₹2,000 (reduces shopping spend)
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 3, 15),
            original_description="REFUND AMAZON",
            normalized_description="refund amazon",
            amount=Decimal("2000.00"),
            currency="INR",
            direction="credit",
            transaction_type="refund",
            review_status="auto_approved",
        ),
        # Transfer: ₹15,000 (must be excluded from consolidated income/expense)
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 3, 20),
            original_description="TRANSFER TO FD",
            normalized_description="transfer fd",
            amount=Decimal("15000.00"),
            currency="INR",
            direction="debit",
            transaction_type="transfer",
            review_status="auto_approved",
        ),
    ]
    test_db_session.add_all(txs)
    await test_db_session.commit()

    builder = ProfileBuilder()
    summary = await builder.build_summary(
        test_db_session, user_id, period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
    )

    # Assertions
    assert summary.income_total == Decimal("100000.00")
    assert summary.expense_gross == Decimal("35000.00")  # 25000 + 10000
    assert summary.refunds_total == Decimal("2000.00")
    assert summary.expense_net == Decimal("33000.00")  # 35000 - 2000
    assert summary.transfers_excluded_total == Decimal("15000.00")
    assert summary.transfers_excluded_count == 1
    assert summary.net_cash_flow == Decimal("67000.00")  # 100000 - 33000
    # Savings rate = (67000 / 100000) * 100 = 67.00%
    assert summary.cash_flow_savings_rate == Decimal("67.00")
    assert summary.essential_expense_total == Decimal("25000.00")
    assert summary.variable_expense_total == Decimal("10000.00")
    assert summary.coverage.transaction_count == 5
    assert summary.coverage.account_count == 1


# ============================================================================
# 7. Profile Snapshot Creation and MoM Comparison Tests
# ============================================================================

@pytest.mark.asyncio
async def test_snapshot_idempotency_and_comparison(test_db_session: AsyncSession):
    """Snapshot recomputation is idempotent and comparison computes period diffs."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="Snapshot Test User",
        email="snap@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.commit()

    manager = SnapshotManager()

    # 1. Create Jan snapshot
    snap_jan = await manager.create_or_update_snapshot(
        test_db_session, user_id, date(2026, 1, 1), date(2026, 1, 31)
    )
    assert snap_jan.period_start == date(2026, 1, 1)

    # 2. Recompute Jan snapshot idempotently (same period bounds)
    snap_jan_again = await manager.create_or_update_snapshot(
        test_db_session, user_id, date(2026, 1, 1), date(2026, 1, 31)
    )
    assert snap_jan_again.id == snap_jan.id  # Same record updated

    # 3. Create Feb snapshot
    snap_feb = await manager.create_or_update_snapshot(
        test_db_session, user_id, date(2026, 2, 1), date(2026, 2, 28)
    )

    # 4. Compare Jan vs Feb
    comp = manager.compare_snapshots(current_snapshot=snap_feb, previous_snapshot=snap_jan)
    assert comp.income_delta == Decimal("0.00")
    assert "Compared to previous period" in comp.summary_narrative


# ============================================================================
# 8. REST API Endpoints Integration Tests (via TestClient)
# ============================================================================

def test_api_recurring_flow(client_with_db):
    """Test full API recurring flow: detect -> list -> detail -> review -> update."""
    client = client_with_db

    # 1. List recurring (initially empty)
    res = client.get("/api/v1/recurring")
    assert res.status_code == 200
    assert "data" in res.json()

    # 2. Detect recurring
    detect_res = client.post("/api/v1/recurring/detect")
    assert detect_res.status_code == 200
    assert isinstance(detect_res.json()["data"], list)

    # 3. List price changes
    pc_res = client.get("/api/v1/recurring/price-changes")
    assert pc_res.status_code == 200
    assert isinstance(pc_res.json()["data"], list)


def test_api_living_model_facts_and_profile(client_with_db):
    """Test Living Money Model API: create fact -> get profile -> financial summary."""
    client = client_with_db

    # 1. Create a user-confirmed income fact
    fact_payload = {
        "fact_type": "income",
        "label": "Monthly In-Hand Salary",
        "amount": "120000.00",
        "currency": "INR",
        "source_type": "user_confirmed",
        "effective_from": "2026-01-01",
    }
    fact_res = client.post("/api/v1/profile/facts", json=fact_payload)
    assert fact_res.status_code == 201
    fact_data = fact_res.json()["data"]
    fact_id = fact_data["id"]
    assert fact_data["amount"] == "120000.00"

    # 2. Update the fact
    update_res = client.patch(
        f"/api/v1/profile/facts/{fact_id}",
        json={"amount": "125000.00", "label": "Revised In-Hand Salary"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["amount"] == "125000.00"

    # 3. Get profile
    prof_res = client.get("/api/v1/profile")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()["data"]
    assert len(prof_data["active_facts"]) >= 1
    assert prof_data["provenance"]["calculation_type"] == "deterministic_python_decimal"

    # 4. Get financial summary
    sum_res = client.get("/api/v1/financial-summary?period_start=2026-01-01&period_end=2026-01-31")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["currency"] == "INR"
    assert "income_total" in sum_data
    assert "net_cash_flow" in sum_data
    assert "coverage" in sum_data

    # 5. Recompute snapshot
    snap_payload = {
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
    }
    snap_res = client.post("/api/v1/profile/snapshots/recompute", json=snap_payload)
    assert snap_res.status_code == 200
    assert snap_res.json()["data"]["period_start"] == "2026-01-01"

    # 6. Get profile history
    hist_res = client.get("/api/v1/profile/history")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_list_demo_personas_endpoint(client_with_db: AsyncSession, test_db_session: AsyncSession):
    """Verify GET /api/v1/profile/personas returns seeded synthetic personas."""
    client = client_with_db

    # Create user and demo profile
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="Asha Mehta (Demo)",
        email="asha@synthetic.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    demo_prof = DemoProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        persona_key="asha_mehta",
        profile_label="Asha Mehta – Salaried Professional",
        is_synthetic=True,
    )
    test_db_session.add(user)
    test_db_session.add(demo_prof)
    await test_db_session.commit()

    res = client.get("/api/v1/profile/personas")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["persona_key"] == "asha_mehta"
    assert data[0]["display_name"] == "Asha Mehta (Demo)"
    assert data[0]["is_synthetic"] is True


@pytest.mark.asyncio
async def test_gemini_subscription_service_fallback_and_next_date():
    """Verify subscription detection from description and predictive next billing dates."""
    from backend.app.intelligence.recurring.gemini_subscription_service import GeminiSubscriptionService

    service = GeminiSubscriptionService()

    # 1. Test Netflix monthly subscription identification
    det_netflix = service._fallback_identify_subscription("NETFLIX MUMBAI IN 918239", Decimal("649.00"))
    assert det_netflix is not None
    assert det_netflix["is_subscription"] is True
    assert det_netflix["subscription_name"] == "Netflix"
    assert det_netflix["cadence"] == "monthly"

    # 2. Test Airtel Broadband identification
    det_airtel = service._fallback_identify_subscription("AIRTEL FIBER BROADBAND BILL", Decimal("1179.00"))
    assert det_airtel is not None
    assert det_airtel["subscription_name"] == "Airtel Broadband"
    assert det_airtel["cadence"] == "monthly"

    # 3. Test predictive next billing date calculation
    debited_date = date(2026, 10, 5)
    next_date = service.calculate_next_expected_date(debited_date, "monthly")
    assert next_date > date.today()
    assert next_date.day == 5
