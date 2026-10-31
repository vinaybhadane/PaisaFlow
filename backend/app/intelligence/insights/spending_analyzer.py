"""Category-wise spending analysis and merchant breakdown engine.

Follows docs/10_FINANCIAL_LOGIC.md:
- Python Decimal arithmetic throughout.
- Own-account transfers strictly excluded.
- Refunds reduce category/total net spend.
- Essential vs discretionary expense segregation.
- Prior period month-over-month comparisons.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.intelligence.recurring.amount_analysis import round_money
from backend.app.models.transaction import Transaction


ESSENTIAL_KEYWORDS = {
    "housing",
    "rent",
    "utilities",
    "electricity",
    "water",
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
class CategorySpendSummary:
    """Category spending breakdown item."""

    category_id: Optional[uuid.UUID]
    category_name: str
    current_spend: Decimal
    previous_spend: Decimal
    change_amount: Decimal
    change_percentage: Optional[Decimal]
    spend_percentage: Decimal
    is_essential: bool
    trend: str  # "increasing", "decreasing", "stable"


@dataclass
class MerchantSpendSummary:
    """Merchant spending summary item."""

    merchant_name: str
    merchant_id: Optional[uuid.UUID]
    total_amount: Decimal
    transaction_count: int
    percentage_of_total: Decimal


@dataclass
class MonthlyTrendItem:
    """Monthly spending trend summary."""

    month_key: str  # "YYYY-MM"
    month_label: str  # "Jan 2026"
    period_start: date
    period_end: date
    income_total: Decimal
    total_spend: Decimal
    essential_spend: Decimal
    variable_spend: Decimal
    net_cash_flow: Decimal


@dataclass
class SpendingAnalysisResult:
    """Consolidated spending analysis result."""

    period_start: date
    period_end: date
    currency: str
    total_gross_expense: Decimal
    total_refunds: Decimal
    total_net_expense: Decimal
    essential_spend: Decimal
    discretionary_spend: Decimal
    essential_percentage: Decimal
    discretionary_percentage: Decimal
    categories: List[CategorySpendSummary]
    top_merchants: List[MerchantSpendSummary]


class SpendingAnalyzer:
    """Analyzer for category spend distributions, merchant concentrations, and trends."""

    async def analyze_period_spending(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> SpendingAnalysisResult:
        """Analyze category spending and top merchants for a date range with prior period comparison."""
        today = date.today()
        if not period_start:
            period_start = today.replace(day=1)
        if not period_end:
            next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_month - timedelta(days=1)

        duration_days = (period_end - period_start).days + 1
        prev_end = period_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=duration_days - 1)

        # 1. Fetch current and previous period transactions
        current_txs = await self._fetch_eligible_transactions(db, user_id, period_start, period_end)

        # If current calendar month has no statement transactions, default to latest active statement month
        if not current_txs:
            latest_tx_stmt = (
                select(Transaction.transaction_date)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.is_excluded.is_(False),
                )
                .order_by(Transaction.transaction_date.desc())
                .limit(1)
            )
            latest_res = await db.execute(latest_tx_stmt)
            latest_date = latest_res.scalar_one_or_none()
            if latest_date and latest_date < period_start:
                period_start = latest_date.replace(day=1)
                next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                period_end = next_month - timedelta(days=1)
                duration_days = (period_end - period_start).days + 1
                prev_end = period_start - timedelta(days=1)
                prev_start = prev_end - timedelta(days=duration_days - 1)
                current_txs = await self._fetch_eligible_transactions(db, user_id, period_start, period_end)

        prev_txs = await self._fetch_eligible_transactions(db, user_id, prev_start, prev_end)

        # 2. Compute current period category and merchant spend
        cat_current: Dict[str, Dict] = {}
        merchant_spend: Dict[str, Dict] = {}
        total_gross = Decimal("0.00")
        total_refunds = Decimal("0.00")
        essential_sum = Decimal("0.00")
        discretionary_sum = Decimal("0.00")

        for tx in current_txs:
            amt = tx.amount or Decimal("0.00")
            if tx.transaction_type == "refund":
                total_refunds += amt
                continue

            total_gross += amt
            cat_name = self._resolve_category_name(tx)
            is_ess = self._is_essential(cat_name, tx.normalized_description)

            if is_ess:
                essential_sum += amt
            else:
                discretionary_sum += amt

            if cat_name not in cat_current:
                cat_current[cat_name] = {
                    "id": tx.category_id,
                    "amount": Decimal("0.00"),
                    "is_essential": is_ess,
                }
            cat_current[cat_name]["amount"] += amt

            # Merchant accumulation
            m_name = (
                getattr(tx.merchant, "display_name", None)
                if tx.merchant
                else getattr(tx, "merchant_name", None)
            ) or tx.normalized_description.title()
            if m_name not in merchant_spend:
                merchant_spend[m_name] = {
                    "id": tx.merchant_id,
                    "amount": Decimal("0.00"),
                    "count": 0,
                }
            merchant_spend[m_name]["amount"] += amt
            merchant_spend[m_name]["count"] += 1

        total_net = max(Decimal("0.00"), total_gross - total_refunds)

        # 3. Compute prior period category spend
        cat_prev: Dict[str, Decimal] = {}
        for tx in prev_txs:
            if tx.transaction_type != "refund":
                c_name = self._resolve_category_name(tx)
                cat_prev[c_name] = cat_prev.get(c_name, Decimal("0.00")) + (tx.amount or Decimal("0.00"))

        # 4. Assemble category summaries with trend detection
        category_summaries: List[CategorySpendSummary] = []
        for name, data in cat_current.items():
            c_amt = round_money(data["amount"])
            p_amt = round_money(cat_prev.get(name, Decimal("0.00")))
            delta = round_money(c_amt - p_amt)

            pct_change: Optional[Decimal] = None
            if p_amt > Decimal("0.00"):
                pct_change = round_money((delta / p_amt) * Decimal("100"))

            spend_pct = (
                round_money((c_amt / total_net) * Decimal("100"))
                if total_net > Decimal("0.00")
                else Decimal("0.00")
            )

            if delta > Decimal("50.00") and (pct_change is None or pct_change > Decimal("5.00")):
                trend = "increasing"
            elif delta < Decimal("-50.00") and (pct_change is not None and pct_change < Decimal("-5.00")):
                trend = "decreasing"
            else:
                trend = "stable"

            category_summaries.append(
                CategorySpendSummary(
                    category_id=data["id"],
                    category_name=name,
                    current_spend=c_amt,
                    previous_spend=p_amt,
                    change_amount=delta,
                    change_percentage=pct_change,
                    spend_percentage=spend_pct,
                    is_essential=data["is_essential"],
                    trend=trend,
                )
            )

        category_summaries.sort(key=lambda c: c.current_spend, reverse=True)

        # 5. Assemble top merchants
        top_merchants: List[MerchantSpendSummary] = []
        for m_name, m_data in merchant_spend.items():
            m_amt = round_money(m_data["amount"])
            m_pct = (
                round_money((m_amt / total_net) * Decimal("100"))
                if total_net > Decimal("0.00")
                else Decimal("0.00")
            )
            top_merchants.append(
                MerchantSpendSummary(
                    merchant_name=m_name,
                    merchant_id=m_data["id"],
                    total_amount=m_amt,
                    transaction_count=m_data["count"],
                    percentage_of_total=m_pct,
                )
            )
        top_merchants.sort(key=lambda m: m.total_amount, reverse=True)

        ess_pct = (
            round_money((essential_sum / total_net) * Decimal("100"))
            if total_net > Decimal("0.00")
            else Decimal("0.00")
        )
        disc_pct = (
            round_money((discretionary_sum / total_net) * Decimal("100"))
            if total_net > Decimal("0.00")
            else Decimal("0.00")
        )

        return SpendingAnalysisResult(
            period_start=period_start,
            period_end=period_end,
            currency="INR",
            total_gross_expense=round_money(total_gross),
            total_refunds=round_money(total_refunds),
            total_net_expense=round_money(total_net),
            essential_spend=round_money(essential_sum),
            discretionary_spend=round_money(discretionary_sum),
            essential_percentage=ess_pct,
            discretionary_percentage=disc_pct,
            categories=category_summaries,
            top_merchants=top_merchants[:10],
        )

    async def get_monthly_trends(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        months_count: int = 6,
    ) -> List[MonthlyTrendItem]:
        """Generate monthly spending and cash flow trends across past N months."""
        today = date.today()
        # Compute first of current month
        curr_m_start = today.replace(day=1)
        trends: List[MonthlyTrendItem] = []

        for i in range(months_count - 1, -1, -1):
            # Calculate month start and end
            year = curr_m_start.year
            month = curr_m_start.month - i
            while month <= 0:
                month += 12
                year -= 1

            m_start = date(year, month, 1)
            next_m = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            m_end = next_m - timedelta(days=1)

            txs = await self._fetch_all_period_transactions(db, user_id, m_start, m_end)

            inc = Decimal("0.00")
            exp_gross = Decimal("0.00")
            ref = Decimal("0.00")
            ess = Decimal("0.00")
            var = Decimal("0.00")

            for tx in txs:
                if tx.is_excluded or tx.transaction_type == "transfer":
                    continue
                amt = tx.amount or Decimal("0.00")
                if tx.transaction_type == "income" and tx.direction == "credit":
                    inc += amt
                elif tx.transaction_type == "refund":
                    ref += amt
                elif tx.transaction_type == "expense" and tx.direction == "debit":
                    exp_gross += amt
                    c_name = self._resolve_category_name(tx)
                    if self._is_essential(c_name, tx.normalized_description):
                        ess += amt
                    else:
                        var += amt

            exp_net = max(Decimal("0.00"), exp_gross - ref)
            net_cf = round_money(inc - exp_net)

            month_key = m_start.strftime("%Y-%m")
            month_label = m_start.strftime("%b %Y")

            trends.append(
                MonthlyTrendItem(
                    month_key=month_key,
                    month_label=month_label,
                    period_start=m_start,
                    period_end=m_end,
                    income_total=round_money(inc),
                    total_spend=round_money(exp_net),
                    essential_spend=round_money(ess),
                    variable_spend=round_money(var),
                    net_cash_flow=net_cf,
                )
            )

        return trends

    async def _fetch_eligible_transactions(
        self, db: AsyncSession, user_id: uuid.UUID, start_date: date, end_date: date
    ) -> List[Transaction]:
        """Fetch non-excluded debit expense and credit refund transactions for spending analysis."""
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.merchant), selectinload(Transaction.category))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded.is_(False),
                Transaction.transaction_type.in_(["expense", "refund"]),
            )
            .order_by(Transaction.transaction_date.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def _fetch_all_period_transactions(
        self, db: AsyncSession, user_id: uuid.UUID, start_date: date, end_date: date
    ) -> List[Transaction]:
        """Fetch all user transactions within a period for trend aggregation."""
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .order_by(Transaction.transaction_date.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    def _resolve_category_name(self, tx: Transaction) -> str:
        """Resolve friendly category name from relationship or description."""
        if tx.category and tx.category.name:
            return tx.category.name
        norm = (tx.normalized_description or "").lower()
        mapping = [
            (["food", "dining", "restaurant", "cafe", "swiggy", "zomato"], "Food & Dining"),
            (["rent", "flat", "apartment", "housing", "society", "maintenance"], "Housing & Rent"),
            (["grocer", "supermarket", "blinkit", "zepto", "instamart", "bigbasket"], "Groceries"),
            (["utilit", "electricity", "water", "broadband", "wifi", "bescom", "airtel"], "Utilities"),
            (["transport", "fuel", "petrol", "diesel", "cab", "uber", "ola", "fastag"], "Transportation"),
            (["shop", "retail", "amazon", "flipkart", "myntra", "zara"], "Shopping"),
            (["health", "medical", "hospital", "pharma", "apollo", "1mg"], "Healthcare"),
            (["entertain", "netflix", "prime", "spotify", "gym", "hotstar"], "Entertainment & Subscriptions"),
            (["loan", "debt", "emi"], "Financial Obligations"),
        ]
        for tokens, cat_name in mapping:
            if any(t in norm for t in tokens):
                return cat_name
        return "Discretionary & Other"

    def _is_essential(self, category_name: str, description: Optional[str]) -> bool:
        """Check whether spending belongs to an essential category."""
        target = f"{category_name.lower()} {(description or '').lower()}"
        return any(kw in target for kw in ESSENTIAL_KEYWORDS)
