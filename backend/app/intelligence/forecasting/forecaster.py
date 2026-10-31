"""Deterministic Financial Forecasting Engine.

Strict rules (from docs/10_FINANCIAL_LOGIC.md and docs/09_AI_INTELLIGENCE_ENGINE.md):
- Deterministic calculations using Python Decimal.
- Strict separation of actual vs estimated values.
- Explicit assumptions and data coverage disclosure.
- No forecasts with fabricated data or when transaction coverage is insufficient.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.living_model.fact_resolver import FinancialFactResolver
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.recurring.amount_analysis import round_money
from backend.app.intelligence.recurring.commitment_service import RecurringCommitmentService


@dataclass
class ForecastMonthItem:
    """Projected financial position for a future month."""

    month_index: int  # 1 for next month, 2 for month after, etc.
    target_month: str  # "YYYY-MM"
    target_month_label: str  # "Apr 2026"
    expected_income: Decimal
    expected_recurring_expenses: Decimal
    expected_variable_expenses: Decimal
    expected_total_expenses: Decimal
    projected_net_cash_flow: Decimal
    projected_cumulative_savings: Decimal
    expected_available_money: Decimal


@dataclass
class ForecastResult:
    """Consolidated forecast result for 1 to 6 months ahead."""

    generated_date: date
    horizon_months: int
    currency: str
    baseline_monthly_income: Decimal
    baseline_recurring_expenses: Decimal
    baseline_variable_expenses: Decimal
    baseline_monthly_expenses: Decimal
    baseline_net_cash_flow: Decimal
    data_coverage_status: str  # "sufficient", "limited", "insufficient"
    is_forecastable: bool
    months: List[ForecastMonthItem]
    assumptions: List[str]
    notes: List[str]


class FinancialForecaster:
    """Forecasting engine generating deterministic 1, 3, and 6-month projections."""

    def __init__(
        self,
        fact_resolver: Optional[FinancialFactResolver] = None,
        profile_builder: Optional[ProfileBuilder] = None,
        commitment_service: Optional[RecurringCommitmentService] = None,
    ):
        self.fact_resolver = fact_resolver or FinancialFactResolver()
        self.profile_builder = profile_builder or ProfileBuilder(self.fact_resolver)
        self.commitment_service = commitment_service or RecurringCommitmentService()

    async def generate_forecast(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        horizon_months: int = 6,
    ) -> ForecastResult:
        """Generate deterministic monthly forecasts for the next N months (default 6)."""
        today = date.today()
        # 1. Fetch current profile summary for baseline
        curr_m_start = today.replace(day=1)
        summary = await self.profile_builder.build_summary(
            db, user_id, period_start=curr_m_start, period_end=today
        )

        # If beginning of month has insufficient transactions, use trailing 30 days for run-rate
        if summary.coverage.transaction_count < 3:
            trailing_start = today - timedelta(days=30)
            summary = await self.profile_builder.build_summary(
                db, user_id, period_start=trailing_start, period_end=today
            )

        # 2. Check active facts and data coverage
        active_facts = await self.fact_resolver.get_active_facts_for_date(db, user_id, as_of_date=today)
        confirmed_income_fact = next(
            (f for f in active_facts if f.fact_type == "income" and f.source_type == "user_confirmed"),
            None,
        )
        has_income = (confirmed_income_fact is not None) or (summary.income_total > Decimal("0.00"))
        coverage_tx_count = summary.coverage.transaction_count

        if coverage_tx_count < 3 and not has_income:
            return ForecastResult(
                generated_date=today,
                horizon_months=horizon_months,
                currency="INR",
                baseline_monthly_income=Decimal("0.00"),
                baseline_recurring_expenses=Decimal("0.00"),
                baseline_variable_expenses=Decimal("0.00"),
                baseline_monthly_expenses=Decimal("0.00"),
                baseline_net_cash_flow=Decimal("0.00"),
                data_coverage_status="insufficient",
                is_forecastable=False,
                months=[],
                assumptions=[
                    "Insufficient transaction data to establish a reliable spending run-rate.",
                    "At least 1 month of statement data required before generating forecasts.",
                ],
                notes=[
                    "Import bank or card statements to view deterministic cash flow projections."
                ],
            )

        # 3. Determine baseline income (prefer user-confirmed fact)

        baseline_income = (
            confirmed_income_fact.amount
            if confirmed_income_fact
            else summary.income_total
        )

        # 4. Recurring obligations monthly equivalent
        baseline_recurring = summary.recurring_commitments_monthly

        # 5. Variable expenses baseline (using current period variable spend)
        baseline_variable = summary.variable_expense_total
        baseline_total_exp = round_money(baseline_recurring + baseline_variable)
        baseline_net_cf = round_money(baseline_income - baseline_total_exp)

        # 6. Build projections month by month
        projected_months: List[ForecastMonthItem] = []
        cumulative_savings = Decimal("0.00")

        for k in range(1, horizon_months + 1):
            # Calculate future month date
            future_year = curr_m_start.year
            future_month = curr_m_start.month + k
            while future_month > 12:
                future_month -= 12
                future_year += 1

            future_date = date(future_year, future_month, 1)
            month_key = future_date.strftime("%Y-%m")
            month_label = future_date.strftime("%b %Y")

            exp_inc = baseline_income
            exp_rec = baseline_recurring
            exp_var = baseline_variable
            exp_tot = baseline_total_exp
            net_cf = baseline_net_cf

            if net_cf > Decimal("0.00"):
                cumulative_savings += net_cf

            avail_money = max(Decimal("0.00"), net_cf)

            projected_months.append(
                ForecastMonthItem(
                    month_index=k,
                    target_month=month_key,
                    target_month_label=month_label,
                    expected_income=exp_inc,
                    expected_recurring_expenses=exp_rec,
                    expected_variable_expenses=exp_var,
                    expected_total_expenses=exp_tot,
                    projected_net_cash_flow=net_cf,
                    projected_cumulative_savings=round_money(cumulative_savings),
                    expected_available_money=avail_money,
                )
            )

        assumptions = [
            f"Baseline income of ₹{baseline_income:,.2f} assumes income stability over the {horizon_months}-month horizon.",
            f"Recurring obligations of ₹{baseline_recurring:,.2f}/month assume active commitments persist without cancellation.",
            f"Variable spending of ₹{baseline_variable:,.2f}/month assumes typical discretionary spend matches current run-rate.",
            "Projections assume zero interest/investment returns and no unmodeled one-off emergencies.",
            "All forecasts are deterministic planning estimates, not promises or guaranteed future balances.",
        ]

        notes = [
            f"Calculated for {horizon_months} months ahead based on {coverage_tx_count} transactions and active commitments.",
            "Estimates automatically update as new statements or user facts are registered.",
        ]

        coverage_status = "sufficient" if coverage_tx_count >= 10 else "limited"

        return ForecastResult(
            generated_date=today,
            horizon_months=horizon_months,
            currency="INR",
            baseline_monthly_income=round_money(baseline_income),
            baseline_recurring_expenses=round_money(baseline_recurring),
            baseline_variable_expenses=round_money(baseline_variable),
            baseline_monthly_expenses=round_money(baseline_total_exp),
            baseline_net_cash_flow=round_money(baseline_net_cf),
            data_coverage_status=coverage_status,
            is_forecastable=True,
            months=projected_months,
            assumptions=assumptions,
            notes=notes,
        )
