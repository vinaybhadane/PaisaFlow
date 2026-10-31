"""Financial Insights Engine generating explainable, evidence-grounded financial observations.

Strict rules:
- Deterministic calculations using Python Decimal.
- Provenance and supporting metrics for every insight.
- Guard against misleading claims when transaction data is insufficient.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.insights.spending_analyzer import SpendingAnalyzer
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.recurring.amount_analysis import round_money
from backend.app.intelligence.recurring.commitment_service import RecurringCommitmentService


@dataclass
class FinancialInsight:
    """Structured financial insight item."""

    insight_type: str
    title: str
    explanation: str
    metric_value: str
    change_percentage: Optional[Decimal]
    period: str
    confidence: str  # "high", "medium", "low"
    severity: str  # "info", "positive", "warning"
    evidence: Dict[str, Any] = field(default_factory=dict)


class InsightsEngine:
    """Generates deterministic financial insights grounded in transaction data and profile facts."""

    def __init__(
        self,
        spending_analyzer: Optional[SpendingAnalyzer] = None,
        profile_builder: Optional[ProfileBuilder] = None,
        commitment_service: Optional[RecurringCommitmentService] = None,
    ):
        self.spending_analyzer = spending_analyzer or SpendingAnalyzer()
        self.profile_builder = profile_builder or ProfileBuilder()
        self.commitment_service = commitment_service or RecurringCommitmentService()

    async def generate_insights(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> List[FinancialInsight]:
        """Generate structured financial insights for the requested period."""
        today = date.today()
        if not period_start:
            period_start = today.replace(day=1)
        if not period_end:
            next_m = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_m - timedelta(days=1)

        period_label = f"{period_start.strftime('%b %d')} - {period_end.strftime('%b %d, %Y')}"

        # 1. Fetch current summary and spending breakdown
        summary = await self.profile_builder.build_summary(
            db, user_id, period_start=period_start, period_end=period_end
        )
        spending = await self.spending_analyzer.analyze_period_spending(
            db, user_id, period_start=period_start, period_end=period_end
        )

        insights: List[FinancialInsight] = []

        # Coverage guard: if empty data, surface transparent coverage insight
        if summary.coverage.transaction_count < 3:
            insights.append(
                FinancialInsight(
                    insight_type="data_coverage",
                    title="Insufficient Transaction History",
                    explanation=(
                        f"Only {summary.coverage.transaction_count} transactions recorded for this period. "
                        "Import at least 1–2 months of statements to unlock personalized trend insights."
                    ),
                    metric_value=f"{summary.coverage.transaction_count} transactions",
                    change_percentage=None,
                    period=period_label,
                    confidence="low",
                    severity="info",
                    evidence={"days_covered": summary.coverage.days_covered},
                )
            )
            return insights

        # 2. Highest Spending Category Insight
        if spending.categories:
            top_cat = spending.categories[0]
            if top_cat.current_spend > Decimal("0.00"):
                insights.append(
                    FinancialInsight(
                        insight_type="highest_spending_category",
                        title=f"Top Spend: {top_cat.category_name}",
                        explanation=(
                            f"{top_cat.category_name} is your largest expense category this period at "
                            f"₹{top_cat.current_spend:,.2f}, representing {top_cat.spend_percentage}% of your total net spending."
                        ),
                        metric_value=f"₹{top_cat.current_spend:,.2f}",
                        change_percentage=top_cat.change_percentage,
                        period=period_label,
                        confidence="high",
                        severity="info",
                        evidence={
                            "category_name": top_cat.category_name,
                            "amount": str(top_cat.current_spend),
                            "percentage": str(top_cat.spend_percentage),
                        },
                    )
                )

        # 3. Unusual Spending Increase Insight
        for cat in spending.categories:
            # Significant spike: >= ₹1,000 increase and >= 20% growth
            if (
                cat.change_amount >= Decimal("1000.00")
                and cat.change_percentage is not None
                and cat.change_percentage >= Decimal("20.00")
            ):
                insights.append(
                    FinancialInsight(
                        insight_type="unusual_spending_increase",
                        title=f"Spending Spike in {cat.category_name}",
                        explanation=(
                            f"{cat.category_name} spending grew by {cat.change_percentage:+.1f}% "
                            f"(+₹{cat.change_amount:,.2f}) compared to the prior period."
                        ),
                        metric_value=f"+₹{cat.change_amount:,.2f}",
                        change_percentage=cat.change_percentage,
                        period=period_label,
                        confidence="high" if cat.previous_spend > Decimal("0.00") else "medium",
                        severity="warning",
                        evidence={
                            "category_name": cat.category_name,
                            "current_spend": str(cat.current_spend),
                            "previous_spend": str(cat.previous_spend),
                            "change_amount": str(cat.change_amount),
                        },
                    )
                )

        # 4. Income vs Expense & Net Cash Flow Insight
        if summary.income_total > Decimal("0.00"):
            if summary.net_cash_flow >= Decimal("0.00"):
                exp_ratio = round_money((summary.expense_net / summary.income_total) * Decimal("100"))
                insights.append(
                    FinancialInsight(
                        insight_type="income_vs_expense",
                        title="Positive Net Cash Flow",
                        explanation=(
                            f"You generated a cash flow surplus of ₹{summary.net_cash_flow:,.2f}. "
                            f"You spent {exp_ratio}% of your ₹{summary.income_total:,.2f} eligible income."
                        ),
                        metric_value=f"+₹{summary.net_cash_flow:,.2f}",
                        change_percentage=None,
                        period=period_label,
                        confidence="high",
                        severity="positive",
                        evidence={
                            "income": str(summary.income_total),
                            "net_expense": str(summary.expense_net),
                            "surplus": str(summary.net_cash_flow),
                        },
                    )
                )
            else:
                deficit = abs(summary.net_cash_flow)
                insights.append(
                    FinancialInsight(
                        insight_type="income_vs_expense",
                        title="Cash Flow Deficit",
                        explanation=(
                            f"Net expenses (₹{summary.expense_net:,.2f}) exceeded income (₹{summary.income_total:,.2f}) "
                            f"by ₹{deficit:,.2f} this period."
                        ),
                        metric_value=f"-₹{deficit:,.2f}",
                        change_percentage=None,
                        period=period_label,
                        confidence="high",
                        severity="warning",
                        evidence={
                            "income": str(summary.income_total),
                            "net_expense": str(summary.expense_net),
                            "deficit": str(deficit),
                        },
                    )
                )

        # 5. Savings Rate Insight
        if summary.cash_flow_savings_rate is not None:
            rate = summary.cash_flow_savings_rate
            sev = "positive" if rate >= Decimal("20.00") else "info" if rate >= Decimal("10.00") else "warning"
            insights.append(
                FinancialInsight(
                    insight_type="savings_rate_trend",
                    title=f"Cash Flow Savings Rate: {rate:.1f}%",
                    explanation=(
                        f"Your estimated cash flow savings rate is {rate:.1f}%. "
                        + ("Healthy surplus above the 20% benchmark." if rate >= Decimal("20.00") else "Consider reviewing discretionary expenses to build a larger emergency cushion.")
                    ),
                    metric_value=f"{rate:.1f}%",
                    change_percentage=None,
                    period=period_label,
                    confidence="high",
                    severity=sev,
                    evidence={"savings_rate": str(rate)},
                )
            )

        # 6. Essential vs Non-Essential Breakdown
        if summary.expense_net > Decimal("0.00"):
            insights.append(
                FinancialInsight(
                    insight_type="essential_vs_discretionary",
                    title=f"Needs vs Wants: {spending.essential_percentage:.0f}% / {spending.discretionary_percentage:.0f}%",
                    explanation=(
                        f"Essential needs (housing, utilities, groceries, healthcare) accounted for "
                        f"₹{spending.essential_spend:,.2f} ({spending.essential_percentage}%), while discretionary wants accounted for "
                        f"₹{spending.discretionary_spend:,.2f} ({spending.discretionary_percentage}%)."
                    ),
                    metric_value=f"{spending.essential_percentage:.0f}% Essential",
                    change_percentage=None,
                    period=period_label,
                    confidence="medium",
                    severity="info",
                    evidence={
                        "essential_spend": str(spending.essential_spend),
                        "discretionary_spend": str(spending.discretionary_spend),
                    },
                )
            )

        # 7. Recurring Payment Burden Insight
        commitments = await self.commitment_service.get_user_commitments(db, user_id)
        active_commitments = [c for c in commitments if c.status in ("confirmed", "likely")]
        if active_commitments and summary.income_total > Decimal("0.00"):
            burden_pct = round_money(
                (summary.recurring_commitments_monthly / summary.income_total) * Decimal("100")
            )
            annual_burden = round_money(summary.recurring_commitments_monthly * Decimal(12))
            sev = "warning" if burden_pct >= Decimal("40.00") else "info"
            insights.append(
                FinancialInsight(
                    insight_type="recurring_payment_burden",
                    title=f"Recurring Commitments: {burden_pct:.1f}% of Income",
                    explanation=(
                        f"{len(active_commitments)} active recurring obligations total ₹{summary.recurring_commitments_monthly:,.2f}/month "
                        f"(~₹{annual_burden:,.2f}/year), taking {burden_pct:.1f}% of your monthly income."
                    ),
                    metric_value=f"{burden_pct:.1f}%",
                    change_percentage=None,
                    period=period_label,
                    confidence="high",
                    severity=sev,
                    evidence={
                        "commitments_count": len(active_commitments),
                        "monthly_total": str(summary.recurring_commitments_monthly),
                        "annual_total": str(annual_burden),
                    },
                )
            )

        return insights

