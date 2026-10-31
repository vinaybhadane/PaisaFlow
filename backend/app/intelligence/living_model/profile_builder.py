"""Living Money Model profile builder and financial summary calculator.

Authoritative implementation of docs/10_FINANCIAL_LOGIC.md and docs/09_AI_INTELLIGENCE_ENGINE.md:
- Python Decimal arithmetic throughout; no floating-point money.
- Exclude transfers, duplicates, and excluded rows from income and expense.
- Account for refunds accurately (disclosing gross vs net expense).
- Calculate cash-flow savings rate only when income is positive.
- Aggregate recurring obligations into monthly planning equivalents.
- Provide data coverage transparency (days covered, accounts, missing periods).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.intelligence.recurring.amount_analysis import (
    calculate_monthly_equivalent,
    round_money,
)
from backend.app.intelligence.living_model.fact_resolver import FinancialFactResolver
from backend.app.models.recurring_commitment import RecurringCommitment
from backend.app.models.transaction import Transaction


ESSENTIAL_CATEGORY_KEYWORDS = {
    "housing",
    "rent",
    "utilities",
    "groceries",
    "supermarket",
    "grocery",
    "healthcare",
    "medical",
    "pharmacy",
    "loan",
    "debt",
    "emi",
    "insurance",
    "education",
    "transport",
    "fuel",
}


@dataclass
class PeriodCoverage:
    """Data coverage metrics for the requested evaluation window."""

    days_covered: int
    transaction_count: int
    account_count: int
    earliest_date: Optional[date]
    latest_date: Optional[date]
    is_complete_month: bool
    coverage_status: str  # "complete", "partial", "empty"
    missing_periods_notes: List[str] = field(default_factory=list)


@dataclass
class FinancialSummaryResult:
    """Deterministic financial summary for a date window."""

    period_start: date
    period_end: date
    currency: str
    income_total: Decimal
    expense_gross: Decimal
    refunds_total: Decimal
    expense_net: Decimal
    transfers_excluded_total: Decimal
    transfers_excluded_count: int
    net_cash_flow: Decimal
    cash_flow_savings_rate: Optional[Decimal]
    essential_expense_total: Decimal
    variable_expense_total: Decimal
    recurring_commitments_monthly: Decimal
    available_money_estimate: Decimal
    coverage: PeriodCoverage
    notes: List[str] = field(default_factory=list)


class ProfileBuilder:
    """Builder for Living Money Model financial profiles and period summaries."""

    def __init__(self, fact_resolver: Optional[FinancialFactResolver] = None):
        self.fact_resolver = fact_resolver or FinancialFactResolver()

    async def build_summary(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> FinancialSummaryResult:
        """Calculate authoritative financial summary for the given period.

        Deterministic: follows docs/10_FINANCIAL_LOGIC.md formulas exactly.
        """
        today = date.today()
        # Default to current month start and end if not provided
        if not period_start:
            period_start = today.replace(day=1)
        if not period_end:
            # End of current month
            next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_month - timedelta(days=1)

        # 1. Fetch transactions in period
        tx_stmt = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
                Transaction.is_excluded.is_(False),
            )
            .order_by(Transaction.transaction_date.asc())
        )
        tx_res = await db.execute(tx_stmt)
        transactions = list(tx_res.scalars().all())

        # 2. Ingestion & filtering logic
        income_total = Decimal("0.00")
        expense_gross = Decimal("0.00")
        refunds_total = Decimal("0.00")
        transfers_total = Decimal("0.00")
        transfers_count = 0
        essential_expenses = Decimal("0.00")
        variable_expenses = Decimal("0.00")

        account_ids = set()
        observed_dates = []

        for tx in transactions:
            account_ids.add(tx.account_id)
            observed_dates.append(tx.transaction_date)
            tx_type = tx.transaction_type
            direction = tx.direction
            amt = tx.amount or Decimal("0.00")

            if tx_type == "transfer":
                # Own-account transfers excluded from consolidated income/expense
                transfers_total += amt
                transfers_count += 1
                continue

            if tx_type == "refund":
                refunds_total += amt
                continue

            if direction == "credit" and tx_type == "income":
                income_total += amt
            elif direction == "debit" and tx_type == "expense":
                expense_gross += amt

                # Classify essential vs variable
                cat_name = ""
                if getattr(tx, "category", None) is not None:
                    cat_name = getattr(tx.category, "name", "") or ""
                elif hasattr(tx, "category_name"):
                    cat_name = getattr(tx, "category_name", "") or ""
                cat_name = cat_name.lower()
                desc = (tx.normalized_description or "").lower()
                is_essential = any(
                    kw in cat_name or kw in desc for kw in ESSENTIAL_CATEGORY_KEYWORDS
                )
                if is_essential:
                    essential_expenses += amt
                else:
                    variable_expenses += amt

        # Net expenses = gross expenses - refunds (floored at zero)
        expense_net = max(Decimal("0.00"), expense_gross - refunds_total)
        net_cash_flow = round_money(income_total - expense_net)

        # Savings rate: (net_cash_flow / income_total) * 100 when income > 0
        savings_rate: Optional[Decimal] = None
        if income_total > Decimal("0.00"):
            savings_rate = round_money((net_cash_flow / income_total) * Decimal("100"))

        # 3. Calculate Recurring Commitments Monthly Equivalent
        rec_stmt = select(RecurringCommitment).where(
            RecurringCommitment.user_id == user_id,
            RecurringCommitment.status.in_(["confirmed", "likely"]),
        )
        rec_res = await db.execute(rec_stmt)
        commitments = list(rec_res.scalars().all())

        recurring_monthly_sum = Decimal("0.00")
        for c in commitments:
            monthly_eq = calculate_monthly_equivalent(
                c.typical_amount, c.cadence, c.estimated_cadence_days
            )
            recurring_monthly_sum += monthly_eq

        recurring_monthly_sum = round_money(recurring_monthly_sum)

        # 4. Integrate Active Financial Facts (Living Money Model)
        active_facts = await self.fact_resolver.get_active_facts_for_date(
            db, user_id, as_of_date=period_end
        )
        confirmed_income_fact = next(
            (f for f in active_facts if f.fact_type == "income" and f.source_type == "user_confirmed"),
            None,
        )

        effective_income = (
            confirmed_income_fact.amount if confirmed_income_fact else income_total
        )

        # Available money (Discretionary surplus):
        # effective_monthly_income - recurring_monthly_commitments - essential_expenses
        available_money = round_money(
            max(Decimal("0.00"), effective_income - recurring_monthly_sum - essential_expenses)
        )

        # 5. Compute Data Coverage
        days_in_period = (period_end - period_start).days + 1
        days_covered = (
            (max(observed_dates) - min(observed_dates)).days + 1 if observed_dates else 0
        )
        tx_count = len(transactions)
        account_count = len(account_ids)

        missing_notes: List[str] = []
        if observed_dates and len(observed_dates) > 1:
            sorted_dates = sorted(observed_dates)
            for i in range(len(sorted_dates) - 1):
                gap = (sorted_dates[i + 1] - sorted_dates[i]).days
                if gap > 14:
                    missing_notes.append(
                        f"Gap of {gap} days between {sorted_dates[i]} and {sorted_dates[i+1]}."
                    )

        is_complete = (
            days_covered >= (days_in_period - 3)
            if period_end <= today
            else days_covered >= (today - period_start).days
        )
        if tx_count == 0:
            coverage_status = "empty"
        elif is_complete:
            coverage_status = "complete"
        else:
            coverage_status = "partial"

        notes = [
            f"Calculated in Asia/Kolkata timezone for period {period_start} to {period_end}.",
            f"{transfers_count} own-account transfers (₹{transfers_total}) excluded from income/expense.",
        ]
        if refunds_total > Decimal("0.00"):
            notes.append(
                f"Gross expense of ₹{expense_gross} reduced by ₹{refunds_total} in refunds to ₹{expense_net} net."
            )

        coverage = PeriodCoverage(
            days_covered=days_covered,
            transaction_count=tx_count,
            account_count=account_count,
            earliest_date=min(observed_dates) if observed_dates else None,
            latest_date=max(observed_dates) if observed_dates else None,
            is_complete_month=is_complete,
            coverage_status=coverage_status,
            missing_periods_notes=missing_notes,
        )

        return FinancialSummaryResult(
            period_start=period_start,
            period_end=period_end,
            currency="INR",
            income_total=round_money(income_total),
            expense_gross=round_money(expense_gross),
            refunds_total=round_money(refunds_total),
            expense_net=round_money(expense_net),
            transfers_excluded_total=round_money(transfers_total),
            transfers_excluded_count=transfers_count,
            net_cash_flow=net_cash_flow,
            cash_flow_savings_rate=savings_rate,
            essential_expense_total=round_money(essential_expenses),
            variable_expense_total=round_money(variable_expenses),
            recurring_commitments_monthly=recurring_monthly_sum,
            available_money_estimate=available_money,
            coverage=coverage,
            notes=notes,
        )
