"""What-If Financial Simulation Engine.

Authoritative implementation of docs/10_FINANCIAL_LOGIC.md and docs/03_FEATURE_SPECIFICATION.md:
- Deterministic Python Decimal arithmetic throughout.
- Scenarios never mutate actual transaction records or confirmed facts.
- Strict isolation of hypothetical assumptions from historical truth.
- Cumulative impact modeling across 3, 6, and 12-month horizons.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ValidationError
from backend.app.intelligence.insights.spending_analyzer import SpendingAnalyzer
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.recurring.amount_analysis import (
    calculate_monthly_equivalent,
    round_money,
)
from backend.app.intelligence.recurring.commitment_service import RecurringCommitmentService


@dataclass
class ScenarioPeriodImpacts:
    """Cumulative financial impact across standard evaluation horizons."""

    monthly_delta: Decimal
    three_month_impact: Decimal
    six_month_impact: Decimal
    twelve_month_impact: Decimal


@dataclass
class SimulationRunResult:
    """Result of running a what-if simulation against baseline profile."""

    scenario_type: str
    title: str
    currency: str
    baseline: Dict[str, Any]
    scenario: Dict[str, Any]
    delta: Dict[str, Any]
    period_impacts: ScenarioPeriodImpacts
    assumptions: List[str]
    notes: List[str]
    calculation_version: str = "1.0.0"


class SimulationEngine:
    """Deterministic simulation engine evaluating what-if financial decisions."""

    def __init__(
        self,
        profile_builder: Optional[ProfileBuilder] = None,
        spending_analyzer: Optional[SpendingAnalyzer] = None,
        commitment_service: Optional[RecurringCommitmentService] = None,
    ):
        self.profile_builder = profile_builder or ProfileBuilder()
        self.spending_analyzer = spending_analyzer or SpendingAnalyzer()
        self.commitment_service = commitment_service or RecurringCommitmentService()

    async def run_simulation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        scenario_type: str,
        input_parameters: Dict[str, Any],
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> SimulationRunResult:
        """Execute what-if simulation deterministically against baseline profile."""
        today = date.today()
        if not period_start:
            period_start = today.replace(day=1)
        if not period_end:
            next_m = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_m - timedelta(days=1)

        # 1. Fetch current baseline
        baseline_summary = await self.profile_builder.build_summary(
            db, user_id, period_start=period_start, period_end=period_end
        )
        baseline_spending = await self.spending_analyzer.analyze_period_spending(
            db, user_id, period_start=period_start, period_end=period_end
        )

        base_income = baseline_summary.income_total
        base_expenses = baseline_summary.expense_net
        base_net_cf = baseline_summary.net_cash_flow
        base_available = baseline_summary.available_money_estimate
        base_savings_rate = baseline_summary.cash_flow_savings_rate or Decimal("0.00")

        # 2. Evaluate specific scenario template
        valid_templates = {
            "reduce_category_percentage",
            "reduce_category_fixed",
            "cancel_recurring",
            "income_change",
            "add_expense",
            "custom_savings",
        }
        if scenario_type not in valid_templates:
            raise ValidationError(
                f"Invalid scenario_type '{scenario_type}'. Allowed: {sorted(list(valid_templates))}"
            )

        updated_income = base_income
        updated_expenses = base_expenses
        monthly_delta = Decimal("0.00")
        assumptions: List[str] = []
        notes: List[str] = []
        scenario_title = "What-If Scenario"

        if scenario_type == "reduce_category_percentage":
            pct_raw = input_parameters.get("reduction_percentage", 0)
            try:
                pct = Decimal(str(pct_raw))
            except Exception:
                raise ValidationError("Invalid reduction_percentage. Must be a valid number.")

            if pct < Decimal("0.00") or pct > Decimal("100.00"):
                raise ValidationError("reduction_percentage must be between 0 and 100.")

            cat_id_raw = input_parameters.get("category_id")
            cat_name_hint = input_parameters.get("category_name", "").strip().lower()

            target_cat = None
            if cat_id_raw:
                try:
                    c_uuid = uuid.UUID(str(cat_id_raw))
                    target_cat = next((c for c in baseline_spending.categories if c.category_id == c_uuid), None)
                except ValueError:
                    pass

            if not target_cat and cat_name_hint:
                target_cat = next(
                    (
                        c
                        for c in baseline_spending.categories
                        if cat_name_hint in c.category_name.lower()
                        or any(w in c.category_name.lower() for w in cat_name_hint.split() if len(w) > 2)
                    ),
                    None,
                )

            if input_parameters.get("baseline_spend"):
                cat_baseline = Decimal(str(input_parameters["baseline_spend"]))
            else:
                cat_baseline = target_cat.current_spend if target_cat else (base_expenses * Decimal("0.20"))
            cat_display_name = target_cat.category_name if target_cat else (cat_name_hint.title() or "Selected Category")

            # Formula from docs/10_FINANCIAL_LOGIC.md line 53
            new_cat_spend = round_money(cat_baseline * (Decimal("1.00") - (pct / Decimal("100.00"))))
            monthly_improvement = round_money(cat_baseline - new_cat_spend)

            updated_expenses = round_money(base_expenses - monthly_improvement)
            monthly_delta = monthly_improvement

            scenario_title = f"Reduce {cat_display_name} by {pct:.0f}%"
            assumptions.append(
                f"Baseline {cat_display_name} spending is ₹{cat_baseline:,.2f} per month."
            )
            assumptions.append(
                f"Assumes {pct:.0f}% reduction persists across all forward-looking evaluation months."
            )

        elif scenario_type == "reduce_category_fixed":
            amt_raw = input_parameters.get("reduction_amount", 0)
            try:
                red_amt = Decimal(str(amt_raw))
            except Exception:
                raise ValidationError("Invalid reduction_amount. Must be a valid positive amount.")

            if red_amt <= Decimal("0.00"):
                raise ValidationError("reduction_amount must be greater than zero.")

            cat_name_hint = input_parameters.get("category_name", "").strip().lower()
            target_cat = next((c for c in baseline_spending.categories if cat_name_hint in c.category_name.lower()), None) if cat_name_hint else None
            cat_baseline = target_cat.current_spend if target_cat else base_expenses
            cat_display_name = target_cat.category_name if target_cat else "Discretionary Spending"

            # Formula from docs/10_FINANCIAL_LOGIC.md line 59
            new_cat_spend = max(Decimal("0.00"), cat_baseline - red_amt)
            monthly_improvement = round_money(cat_baseline - new_cat_spend)

            updated_expenses = round_money(base_expenses - monthly_improvement)
            monthly_delta = monthly_improvement

            scenario_title = f"Reduce {cat_display_name} by ₹{red_amt:,.2f}"
            if red_amt > cat_baseline:
                notes.append(
                    f"Requested reduction of ₹{red_amt:,.2f} exceeded baseline spending of ₹{cat_baseline:,.2f}; reduction capped at baseline."
                )

        elif scenario_type == "cancel_recurring":
            com_id_raw = input_parameters.get("commitment_id")
            com_name_hint = input_parameters.get("display_name", "").strip()

            commitment = None
            if com_id_raw:
                try:
                    c_uuid = uuid.UUID(str(com_id_raw))
                    commitment = await self.commitment_service.get_commitment_by_id(db, user_id, c_uuid)
                except Exception:
                    pass

            if not commitment and com_name_hint:
                all_c = await self.commitment_service.get_user_commitments(db, user_id)
                commitment = next((c for c in all_c if com_name_hint.lower() in c.display_name.lower()), None)

            if commitment:
                c_name = commitment.display_name
                monthly_savings = calculate_monthly_equivalent(
                    commitment.typical_amount, commitment.cadence, commitment.estimated_cadence_days
                )
            else:
                c_name = com_name_hint or "Subscription"
                monthly_savings = Decimal(str(input_parameters.get("monthly_amount", "499.00")))

            updated_expenses = round_money(max(Decimal("0.00"), base_expenses - monthly_savings))
            monthly_delta = monthly_savings

            scenario_title = f"Cancel {c_name}"
            assumptions.append(
                f"Monthly planning equivalent of {c_name} is ₹{monthly_savings:,.2f}."
            )
            assumptions.append(
                "Hypothetical future scenario only. Actual cancellation is not performed with merchant."
            )

        elif scenario_type == "income_change":
            amt_raw = input_parameters.get("income_change_amount", 0)
            try:
                inc_change = Decimal(str(amt_raw))
            except Exception:
                raise ValidationError("Invalid income_change_amount.")

            updated_income = round_money(base_income + inc_change)
            monthly_delta = inc_change
            sign_str = "+" if inc_change >= Decimal("0.00") else ""
            scenario_title = f"Income Change: {sign_str}₹{inc_change:,.2f}/month"
            assumptions.append(
                f"New monthly income projected at ₹{updated_income:,.2f}."
            )

        elif scenario_type == "add_expense":
            amt_raw = input_parameters.get("expense_amount", 0)
            try:
                exp_add = Decimal(str(amt_raw))
            except Exception:
                raise ValidationError("Invalid expense_amount. Must be a valid positive amount.")

            if exp_add <= Decimal("0.00"):
                raise ValidationError("expense_amount must be greater than zero.")

            label = input_parameters.get("expense_label", "New Expense").strip()
            updated_expenses = round_money(base_expenses + exp_add)
            monthly_delta = -exp_add  # Negative impact on surplus
            scenario_title = f"Add {label} (₹{exp_add:,.2f}/mo)"
            assumptions.append(
                f"Adds ₹{exp_add:,.2f}/month to planned expenses starting next month."
            )

        elif scenario_type == "custom_savings":
            amt_raw = input_parameters.get("monthly_savings_amount", 0)
            try:
                sav_amt = Decimal(str(amt_raw))
            except Exception:
                raise ValidationError("Invalid monthly_savings_amount.")

            if sav_amt <= Decimal("0.00"):
                raise ValidationError("monthly_savings_amount must be greater than zero.")

            # Additional savings dedicated from available money
            monthly_delta = sav_amt
            scenario_title = f"Save Additional ₹{sav_amt:,.2f}/month"
            assumptions.append(
                f"Allocates ₹{sav_amt:,.2f}/month directly toward savings goals."
            )

        # 3. Calculate updated net cash flow and available money
        updated_net_cf = round_money(updated_income - updated_expenses)
        updated_available = max(Decimal("0.00"), base_available + monthly_delta)
        updated_savings_rate = (
            round_money((updated_net_cf / updated_income) * Decimal("100"))
            if updated_income > Decimal("0.00")
            else Decimal("0.00")
        )

        # 4. Multi-horizon impacts: 3, 6, 12 months (docs/10_FINANCIAL_LOGIC.md lines 55, 78)
        impacts = ScenarioPeriodImpacts(
            monthly_delta=round_money(monthly_delta),
            three_month_impact=round_money(monthly_delta * Decimal(3)),
            six_month_impact=round_money(monthly_delta * Decimal(6)),
            twelve_month_impact=round_money(monthly_delta * Decimal(12)),
        )

        assumptions.extend([
            "Annualized and multi-period impacts assume stable behavior over 3, 6, and 12 months.",
            "All calculations are deterministic and assume zero investment return or inflation.",
            "Actual transaction history and user-confirmed facts remain 100% unaltered.",
        ])

        return SimulationRunResult(
            scenario_type=scenario_type,
            title=input_parameters.get("custom_title") or scenario_title,
            currency="INR",
            baseline={
                "monthly_income": str(base_income),
                "monthly_expenses": str(base_expenses),
                "net_cash_flow": str(base_net_cf),
                "available_money": str(base_available),
                "savings_rate": str(base_savings_rate),
            },
            scenario={
                "monthly_income": str(updated_income),
                "monthly_expenses": str(updated_expenses),
                "net_cash_flow": str(updated_net_cf),
                "available_money": str(updated_available),
                "savings_rate": str(updated_savings_rate),
            },
            delta={
                "monthly_income_delta": str(round_money(updated_income - base_income)),
                "monthly_expense_delta": str(round_money(updated_expenses - base_expenses)),
                "net_cash_flow_delta": str(round_money(updated_net_cf - base_net_cf)),
                "available_money_delta": str(round_money(monthly_delta)),
                "savings_rate_delta": str(round_money(updated_savings_rate - base_savings_rate)),
            },
            period_impacts=impacts,
            assumptions=assumptions,
            notes=notes,
            calculation_version="1.0.0",
        )
