"""Automated test suite for Phase 6: Financial Insights, Spending Analysis, Forecasting & What-If Simulations.

Validates:
1. Spending Analyzer (category breakdown, essential/discretionary, refunds, transfer exclusion, top merchants, trends)
2. Insights Engine (top spend, spending spikes, net cash flow, savings rate, recurring burden, coverage guard)
3. Financial Forecaster (1, 3, 6 month deterministic projections, coverage gating, assumptions)
4. What-If Simulation Engine (reduce %, reduce fixed, cancel recurring, income change, add expense, savings)
5. Multi-horizon impacts (3, 6, 12 months) and scenario immutability of original financial records
6. Scenario CRUD and side-by-side comparison matrix
7. REST API Endpoints for /insights, /spending, /forecast, /simulations
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.forecasting.forecaster import FinancialForecaster
from backend.app.intelligence.insights.insights_engine import InsightsEngine
from backend.app.intelligence.insights.spending_analyzer import SpendingAnalyzer
from backend.app.intelligence.simulations.scenario_service import ScenarioService
from backend.app.intelligence.simulations.simulation_engine import SimulationEngine
from backend.app.models.account import Account
from backend.app.models.financial_fact import FinancialFact
from backend.app.models.recurring_commitment import RecurringCommitment
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


# ============================================================================
# 1. Spending Analyzer Unit & Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_spending_analyzer_categories_and_refunds(test_db_session: AsyncSession):
    """Verify category spend breakdown, essential vs discretionary, and refund net reductions."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        display_name="Spending User",
        email="spending@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Checking Account",
        account_type="checking",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    # Seed transactions for April 2026
    txs = [
        # Essential: Rent ₹20,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 2),
            original_description="FLAT RENT",
            normalized_description="housing rent",
            amount=Decimal("20000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        # Essential: Groceries ₹6,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 5),
            original_description="BIGBASKET GROCERIES",
            normalized_description="groceries bigbasket",
            amount=Decimal("6000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        # Discretionary: Dining ₹4,000
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 10),
            original_description="SWIGGY DINING",
            normalized_description="swiggy dining",
            amount=Decimal("4000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        # Refund: ₹1,000 (reduces total net expense)
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 12),
            original_description="SWIGGY REFUND",
            normalized_description="refund swiggy",
            amount=Decimal("1000.00"),
            currency="INR",
            direction="credit",
            transaction_type="refund",
        ),
        # Transfer: ₹10,000 (must be excluded from spending analysis)
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 15),
            original_description="SELF TRANSFER",
            normalized_description="transfer savings",
            amount=Decimal("10000.00"),
            currency="INR",
            direction="debit",
            transaction_type="transfer",
        ),
    ]
    test_db_session.add_all(txs)
    await test_db_session.commit()

    analyzer = SpendingAnalyzer()
    res = await analyzer.analyze_period_spending(
        test_db_session, user_id, period_start=date(2026, 4, 1), period_end=date(2026, 4, 30)
    )

    # 20000 + 6000 + 4000 = 30000 gross
    assert res.total_gross_expense == Decimal("30000.00")
    assert res.total_refunds == Decimal("1000.00")
    # 30000 - 1000 = 29000 net
    assert res.total_net_expense == Decimal("29000.00")
    # Essential = 20000 + 6000 = 26000
    assert res.essential_spend == Decimal("26000.00")
    # Discretionary = 4000
    assert res.discretionary_spend == Decimal("4000.00")
    assert len(res.top_merchants) >= 1


@pytest.mark.asyncio
async def test_monthly_trends(test_db_session: AsyncSession):
    """Verify monthly trend aggregation across historical periods."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        display_name="Trend User",
        email="trend@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Checking",
        account_type="checking",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    analyzer = SpendingAnalyzer()
    trends = await analyzer.get_monthly_trends(test_db_session, user_id, months_count=3)
    assert len(trends) == 3
    assert trends[-1].income_total >= Decimal("0.00")


# ============================================================================
# 2. Insights Engine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_insights_engine_generation(test_db_session: AsyncSession):
    """Verify insights generation for top spend, cash flow, and recurring burden."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        display_name="Insights User",
        email="insights@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Primary",
        account_type="savings",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    # Seed salary and expenses
    txs = [
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 1),
            original_description="SALARY",
            normalized_description="salary credited",
            amount=Decimal("80000.00"),
            currency="INR",
            direction="credit",
            transaction_type="income",
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 3),
            original_description="RENT",
            normalized_description="housing rent",
            amount=Decimal("25000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 10),
            original_description="ELECTRONICS",
            normalized_description="laptop emi",
            amount=Decimal("15000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
    ]
    # Add recurring commitment
    commitment = RecurringCommitment(
        user_id=user_id,
        display_name="Broadband Internet",
        cadence="monthly",
        typical_amount=Decimal("1200.00"),
        status="confirmed",
        currency="INR",
        confidence="high",
    )
    test_db_session.add_all(txs + [commitment])
    await test_db_session.commit()

    engine = InsightsEngine()
    insights = await engine.generate_insights(
        test_db_session, user_id, period_start=date(2026, 4, 1), period_end=date(2026, 4, 30)
    )

    assert len(insights) >= 3
    types = [i.insight_type for i in insights]
    assert "highest_spending_category" in types
    assert "income_vs_expense" in types
    assert "recurring_payment_burden" in types


@pytest.mark.asyncio
async def test_insights_engine_insufficient_data_guard(test_db_session: AsyncSession):
    """Insufficient transaction history must yield an educational coverage insight, not false spikes."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="Empty User",
        email="empty@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.commit()

    engine = InsightsEngine()
    insights = await engine.generate_insights(test_db_session, user_id)
    assert len(insights) == 1
    assert insights[0].insight_type == "data_coverage"
    assert "Insufficient Transaction History" in insights[0].title


# ============================================================================
# 3. Financial Forecaster Tests
# ============================================================================

@pytest.mark.asyncio
async def test_financial_forecaster_projections(test_db_session: AsyncSession):
    """Verify deterministic 1, 3, and 6-month projections."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        display_name="Forecast User",
        email="forecast@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Account",
        account_type="checking",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    # Confirmed income fact: ₹90,000
    fact = FinancialFact(
        user_id=user_id,
        fact_type="income",
        label="Monthly Salary",
        amount=Decimal("90000.00"),
        source_type="user_confirmed",
        effective_from=date(2026, 1, 1),
    )
    # Recurring commitment: ₹20,000
    commitment = RecurringCommitment(
        user_id=user_id,
        display_name="Apartment Rent",
        cadence="monthly",
        typical_amount=Decimal("20000.00"),
        status="confirmed",
        currency="INR",
        confidence="high",
    )
    # Variable transactions
    txs = [
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date.today() - timedelta(days=5),
            original_description="GROCERIES",
            normalized_description="groceries",
            amount=Decimal("10000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date.today() - timedelta(days=2),
            original_description="DINING",
            normalized_description="dining",
            amount=Decimal("5000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date.today() - timedelta(days=1),
            original_description="CAB",
            normalized_description="uber cab",
            amount=Decimal("1000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
    ]
    test_db_session.add_all([fact, commitment] + txs)
    await test_db_session.commit()

    forecaster = FinancialForecaster()
    res = await forecaster.generate_forecast(test_db_session, user_id, horizon_months=6)

    assert res.is_forecastable is True
    assert res.baseline_monthly_income == Decimal("90000.00")
    assert res.baseline_recurring_expenses == Decimal("20000.00")
    assert len(res.months) == 6
    assert res.months[0].expected_income == Decimal("90000.00")
    assert res.months[0].expected_recurring_expenses == Decimal("20000.00")
    assert res.months[0].projected_net_cash_flow > Decimal("0.00")
    assert res.months[5].projected_cumulative_savings > res.months[0].projected_cumulative_savings
    assert len(res.assumptions) >= 3


# ============================================================================
# 4. What-If Simulation Engine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_simulation_reduce_category_percentage(test_db_session: AsyncSession):
    """Verify category percentage reduction scenario: B * (1 - p/100)."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        display_name="Sim User",
        email="sim@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=account_id,
        user_id=user_id,
        display_name="Checking",
        account_type="checking",
        currency="INR",
    )
    test_db_session.add_all([user, account])
    await test_db_session.commit()

    # Seed transactions with dining spend of ₹10,000
    txs = [
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 1),
            original_description="SALARY",
            normalized_description="salary",
            amount=Decimal("50000.00"),
            currency="INR",
            direction="credit",
            transaction_type="income",
        ),
        Transaction(
            user_id=user_id,
            account_id=account_id,
            transaction_date=date(2026, 4, 5),
            original_description="RESTAURANT",
            normalized_description="food restaurant",
            amount=Decimal("10000.00"),
            currency="INR",
            direction="debit",
            transaction_type="expense",
        ),
    ]
    test_db_session.add_all(txs)
    await test_db_session.commit()

    engine = SimulationEngine()
    res = await engine.run_simulation(
        test_db_session,
        user_id,
        scenario_type="reduce_category_percentage",
        input_parameters={"reduction_percentage": "30", "category_name": "food"},
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
    )

    # 30% reduction on ₹10,000 = ₹3,000 improvement per month
    assert res.period_impacts.monthly_delta == Decimal("3000.00")
    assert res.period_impacts.three_month_impact == Decimal("9000.00")
    assert res.period_impacts.six_month_impact == Decimal("18000.00")
    assert res.period_impacts.twelve_month_impact == Decimal("36000.00")
    assert res.scenario["monthly_expenses"] == "7000.00"

    # Verify original transactions remain unchanged
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    r = await test_db_session.execute(stmt)
    records = list(r.scalars().all())
    assert len(records) == 2
    assert records[1].amount == Decimal("10000.00")  # Immutable


@pytest.mark.asyncio
async def test_simulation_cancel_recurring(test_db_session: AsyncSession):
    """Verify subscription cancellation scenario without modifying actual recurring records."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="Cancel User",
        email="cancel@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    commitment = RecurringCommitment(
        user_id=user_id,
        display_name="Gym Membership",
        cadence="monthly",
        typical_amount=Decimal("2500.00"),
        status="confirmed",
        currency="INR",
        confidence="high",
    )
    test_db_session.add_all([user, commitment])
    await test_db_session.commit()

    engine = SimulationEngine()
    res = await engine.run_simulation(
        test_db_session,
        user_id,
        scenario_type="cancel_recurring",
        input_parameters={"commitment_id": str(commitment.id)},
    )

    assert res.period_impacts.monthly_delta == Decimal("2500.00")
    assert res.period_impacts.twelve_month_impact == Decimal("30000.00")
    assert "Actual cancellation is not performed" in res.assumptions[1]

    # Commitment status in DB must remain confirmed!
    refreshed_c = await test_db_session.get(RecurringCommitment, commitment.id)
    assert refreshed_c.status == "confirmed"


# ============================================================================
# 5. Scenario CRUD and Comparison Tests
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_service_crud_and_compare(test_db_session: AsyncSession):
    """Verify saving, listing, updating, deleting, and comparing scenarios."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="CRUD User",
        email="crud@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.commit()

    service = ScenarioService()

    # 1. Create scenario 1
    s1 = await service.create_scenario(
        db=test_db_session,
        user_id=user_id,
        title="Scenario A: Reduce Dining",
        scenario_type="reduce_category_percentage",
        input_parameters={"reduction_percentage": "20"},
        baseline_result={"expenses": "20000.00"},
        scenario_result={
            "delta": {"available_money_delta": "2000.00"},
            "period_impacts": {"twelve_month_impact": "24000.00"},
            "scenario": {"savings_rate": "35.00"},
        },
        assumptions={"note": "Test assumption"},
    )
    assert s1.title == "Scenario A: Reduce Dining"

    # 2. Create scenario 2
    s2 = await service.create_scenario(
        db=test_db_session,
        user_id=user_id,
        title="Scenario B: Cancel Gym",
        scenario_type="cancel_recurring",
        input_parameters={"monthly_amount": "2500"},
        baseline_result={"expenses": "20000.00"},
        scenario_result={
            "delta": {"available_money_delta": "2500.00"},
            "period_impacts": {"twelve_month_impact": "30000.00"},
            "scenario": {"savings_rate": "38.00"},
        },
        assumptions={"note": "Test assumption"},
    )

    # 3. List
    scenarios = await service.list_user_scenarios(test_db_session, user_id)
    assert len(scenarios) == 2

    # 4. Compare
    comparison = await service.compare_scenarios(test_db_session, user_id, [s1.id, s2.id])
    assert comparison["scenario_count"] == 2
    assert comparison["scenarios"][0]["monthly_delta"] in ("2000.00", "2500.00")

    # 5. Update
    updated = await service.update_scenario(test_db_session, user_id, s1.id, title="Revised Scenario A")
    assert updated.title == "Revised Scenario A"

    # 6. Delete
    deleted = await service.delete_scenario(test_db_session, user_id, s1.id)
    assert deleted is True

    remaining = await service.list_user_scenarios(test_db_session, user_id)
    assert len(remaining) == 1


# ============================================================================
# 6. REST API Endpoints Integration Tests (via TestClient)
# ============================================================================

def test_api_insights_and_spending(client_with_db):
    """Test /api/v1/insights and /api/v1/spending endpoints."""
    client = client_with_db

    # 1. Insights endpoint
    ins_res = client.get("/api/v1/insights")
    assert ins_res.status_code == 200
    assert "data" in ins_res.json()
    assert isinstance(ins_res.json()["data"], list)

    # 2. Spending categories endpoint
    cat_res = client.get("/api/v1/spending/categories")
    assert cat_res.status_code == 200
    data = cat_res.json()["data"]
    assert "total_net_expense" in data
    assert "categories" in data

    # 3. Spending trends endpoint
    trend_res = client.get("/api/v1/spending/trends?months=6")
    assert trend_res.status_code == 200
    assert len(trend_res.json()["data"]) == 6

    # 4. Top merchants endpoint
    merch_res = client.get("/api/v1/spending/merchants")
    assert merch_res.status_code == 200
    assert isinstance(merch_res.json()["data"], list)


def test_api_forecast(client_with_db):
    """Test /api/v1/forecast endpoint."""
    client = client_with_db
    res = client.get("/api/v1/forecast?horizon=6")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "is_forecastable" in data
    assert "assumptions" in data
    assert data["currency"] == "INR"


def test_api_simulation_lifecycle(client_with_db):
    """Test full simulation API lifecycle: run -> save -> list -> get -> update -> delete."""
    client = client_with_db

    # 1. Run simulation on the fly
    run_payload = {
        "scenario_type": "reduce_category_percentage",
        "input_parameters": {
            "reduction_percentage": "20",
            "category_name": "Food & Dining",
        },
    }
    run_res = client.post("/api/v1/simulations/run", json=run_payload)
    assert run_res.status_code == 200
    sim_data = run_res.json()["data"]
    assert "period_impacts" in sim_data
    assert "monthly_delta" in sim_data["period_impacts"]

    # 2. Save scenario
    save_payload = {
        "title": "API Test Scenario",
        "scenario_type": "reduce_category_percentage",
        "input_parameters": {"reduction_percentage": "20"},
        "baseline_result": sim_data["baseline"],
        "scenario_result": sim_data["scenario"],
        "assumptions": {"assumptions": sim_data["assumptions"]},
    }
    save_res = client.post("/api/v1/simulations", json=save_payload)
    assert save_res.status_code == 201
    saved_scenario = save_res.json()["data"]
    scenario_id = saved_scenario["id"]

    # 3. List scenarios
    list_res = client.get("/api/v1/simulations")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 4. Get scenario
    get_res = client.get(f"/api/v1/simulations/{scenario_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["title"] == "API Test Scenario"

    # 5. Patch scenario
    patch_res = client.patch(
        f"/api/v1/simulations/{scenario_id}", json={"title": "Updated API Test Scenario"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["title"] == "Updated API Test Scenario"

    # 6. Delete scenario
    del_res = client.delete(f"/api/v1/simulations/{scenario_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["status"] == "deleted"
