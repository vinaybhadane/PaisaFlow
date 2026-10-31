"""Deterministic Financial Context Builder for AI Coach.

Prepares strictly bounded, user-isolated, factual financial summaries
for prompt injection into the Gemini LLM.
Rule: The LLM is never the source of truth for arithmetic; all metrics
injected into context are computed deterministically with Decimal.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.forecasting.forecaster import FinancialForecaster
from backend.app.intelligence.insights.insights_engine import InsightsEngine
from backend.app.intelligence.living_model.engine import LivingMoneyModelEngine


class FinancialContextBuilder:
    """Builds structured and bounded financial context for a user."""

    def __init__(
        self,
        living_engine: Optional[LivingMoneyModelEngine] = None,
        insights_engine: Optional[InsightsEngine] = None,
        forecaster: Optional[FinancialForecaster] = None,
    ):
        self.living_engine = living_engine or LivingMoneyModelEngine()
        self.insights_engine = insights_engine or InsightsEngine()
        self.forecaster = forecaster or FinancialForecaster()

    async def build_context(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Compile complete deterministic financial context and grounded facts list."""
        target_date = as_of_date or date.today()

        # 1. Living Profile & Current Period Summary
        profile = await self.living_engine.get_living_profile(
            db, user_id, as_of_date=target_date
        )
        summary = profile.get("current_period_summary", {})
        active_facts = profile.get("active_facts", [])

        # 2. Insights
        insights = await self.insights_engine.generate_insights(
            db, user_id, period_end=target_date
        )

        # 3. Forecast
        forecast = await self.forecaster.generate_forecast(
            db, user_id, horizon_months=3
        )

        # 4. Extract Category Breakdown from profile summary
        category_breakdown = summary.get("categories", [])
        top_categories = sorted(
            [c for c in category_breakdown if c.get("direction") == "expense" or c.get("amount", Decimal("0")) > 0],
            key=lambda x: Decimal(str(x.get("amount", 0))),
            reverse=True,
        )[:5]

        # 5. Extract Recurring Commitments
        commitments = await self.living_engine.commitment_service.get_user_commitments(
            db, user_id, status="confirmed"
        )
        if not commitments:
            commitments = await self.living_engine.commitment_service.get_user_commitments(
                db, user_id, status="likely"
            )

        total_recurring_monthly = Decimal("0.00")
        recurring_list = []
        for c in commitments:
            monthly_equiv = c.typical_amount
            if c.cadence == "yearly":
                monthly_equiv = c.typical_amount / Decimal("12")
            elif c.cadence == "weekly":
                monthly_equiv = c.typical_amount * Decimal("4.33")
            total_recurring_monthly += monthly_equiv
            merchant_name = getattr(c, "display_name", None) or "Recurring Payee"
            if not merchant_name and getattr(c, "merchant", None) and hasattr(c.merchant, "canonical_name"):
                merchant_name = c.merchant.canonical_name

            recurring_list.append({
                "merchant": merchant_name,
                "cadence": c.cadence,
                "amount": f"₹{c.typical_amount:,.2f}",
                "monthly_equivalent": f"₹{monthly_equiv:,.2f}",
                "status": c.status,
            })

        # 6. Format Grounded Facts for UI & Verification
        income_str = summary.get("income_total", "0.00")
        expense_str = summary.get("expense_net", "0.00")
        cash_flow_str = summary.get("net_cash_flow", "0.00")
        savings_rate_str = summary.get("savings_rate", "0%")

        grounded_facts: List[Dict[str, str]] = [
            {"label": "Current Period", "value": f"{summary.get('period_start', '')} to {summary.get('period_end', '')}"},
            {"label": "Total Inflow (Income)", "value": f"₹{Decimal(income_str):,.2f}"},
            {"label": "Total Net Outflow (Expenses)", "value": f"₹{Decimal(expense_str):,.2f}"},
            {"label": "Net Cash Flow Surplus", "value": f"₹{Decimal(cash_flow_str):,.2f}"},
            {"label": "Savings Rate", "value": savings_rate_str},
            {"label": "Active Recurring Commitments", "value": f"{len(recurring_list)} (Total Monthly ~₹{total_recurring_monthly:,.2f})"},
        ]

        if top_categories:
            top_cat_summary = ", ".join([
                f"{c.get('category_name', 'Other')}: ₹{Decimal(str(c.get('amount', 0))):,.2f}"
                for c in top_categories[:3]
            ])
            grounded_facts.append({"label": "Top Spending Categories", "value": top_cat_summary})

        # 7. Construct clean Prompt Context String
        context_text = f"""--- USER FINANCIAL PROFILE (GROUNDED TRUTH) ---
Currency: INR (₹)
Locale: en-IN (Asia/Kolkata)
Period: {summary.get('period_start')} to {summary.get('period_end')}
Data Coverage: Confirmed transaction records only (Synthetic demonstration data)

1. CURRENT PERIOD AGGREGATES:
- Total Income: ₹{Decimal(income_str):,.2f}
- Total Net Expenses: ₹{Decimal(expense_str):,.2f}
- Net Cash Flow: ₹{Decimal(cash_flow_str):,.2f}
- Savings Rate: {savings_rate_str}

2. TOP EXPENSE CATEGORIES:
"""
        if top_categories:
            for cat in top_categories:
                context_text += f"- {cat.get('category_name', 'Uncategorized')}: ₹{Decimal(str(cat.get('amount', 0))):,.2f} ({cat.get('share_percentage', '0%')} of total expenses)\n"
        else:
            context_text += "- None recorded in this period.\n"

        context_text += f"\n3. ACTIVE RECURRING COMMITMENTS (Total Monthly Est: ₹{total_recurring_monthly:,.2f}):\n"
        if recurring_list:
            for r in recurring_list:
                context_text += f"- {r['merchant']}: {r['amount']} ({r['cadence']}) [Status: {r['status']}]\n"
        else:
            context_text += "- No recurring commitments detected.\n"

        context_text += "\n4. ACTIVE CONFIRMED FINANCIAL FACTS (Living Model):\n"
        if active_facts:
            for f in active_facts:
                context_text += f"- {f['label']} ({f['fact_type']}): ₹{Decimal(f['amount']):,.2f} [Source: {f['source_type']}, Confidence: {f['confidence']}]\n"
        else:
            context_text += "- No baseline financial facts registered.\n"

        context_text += "\n5. ALGORITHMIC INSIGHTS & DETECTED PATTERNS:\n"
        if insights:
            for ins in insights[:4]:
                context_text += f"- [{ins.severity.upper()}] {ins.title}: {ins.explanation}\n"
        else:
            context_text += "- Spending appears within typical historical variance.\n"

        context_text += "\n6. 3-MONTH DETERMINISTIC FORECAST:\n"
        context_text += f"- Baseline Monthly Inflow: ₹{forecast.baseline_monthly_income:,.2f}\n"
        context_text += f"- Baseline Monthly Outflow: ₹{forecast.baseline_monthly_expenses:,.2f}\n"
        context_text += f"- Baseline Monthly Net Surplus: ₹{forecast.baseline_net_cash_flow:,.2f}\n"
        if forecast and hasattr(forecast, "months"):
            for m in forecast.months:
                context_text += f"- Month {m.month_index} ({m.target_month_label}): Expected Net ₹{m.projected_net_cash_flow:,.2f}, Cumulative Savings ₹{m.projected_cumulative_savings:,.2f}\n"

        context_text += "\n--- END FINANCIAL PROFILE ---\n"

        return {
            "context_text": context_text,
            "grounded_facts": grounded_facts,
            "summary": summary,
            "top_categories": top_categories,
            "recurring_list": recurring_list,
            "total_recurring_monthly": str(total_recurring_monthly),
            "forecast": forecast,
            "insights": insights,
        }
