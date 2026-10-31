"""Living Money Model coordinator engine.

Integrates active facts, recurring obligations, period financial aggregations,
and historical snapshots into a cohesive Living Money Model using AsyncSession.
"""

from datetime import date
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.living_model.fact_resolver import FinancialFactResolver
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.living_model.snapshots import SnapshotManager
from backend.app.intelligence.recurring.commitment_service import RecurringCommitmentService


class LivingMoneyModelEngine:
    """Coordinator engine for the Living Money Model."""

    def __init__(
        self,
        fact_resolver: Optional[FinancialFactResolver] = None,
        profile_builder: Optional[ProfileBuilder] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        commitment_service: Optional[RecurringCommitmentService] = None,
    ):
        self.fact_resolver = fact_resolver or FinancialFactResolver()
        self.profile_builder = profile_builder or ProfileBuilder(self.fact_resolver)
        self.snapshot_manager = snapshot_manager or SnapshotManager(self.profile_builder)
        self.commitment_service = commitment_service or RecurringCommitmentService()

    async def get_living_profile(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Compile the complete Living Money Model profile as of a specific date."""
        target_date = as_of_date or date.today()

        # 1. Fetch active financial facts
        active_facts = await self.fact_resolver.get_active_facts_for_date(
            db, user_id, as_of_date=target_date
        )

        # 2. Compute current month financial summary
        period_start = target_date.replace(day=1)
        summary = await self.profile_builder.build_summary(
            db, user_id, period_start=period_start, period_end=target_date
        )

        # 3. Fetch user's active recurring commitments
        commitments = await self.commitment_service.get_user_commitments(
            db, user_id, status="confirmed"
        )
        if not commitments:
            # Also include likely commitments if none confirmed
            commitments = await self.commitment_service.get_user_commitments(
                db, user_id, status="likely"
            )

        return {
            "user_id": str(user_id),
            "as_of_date": target_date.isoformat(),
            "active_facts": [
                {
                    "id": str(f.id),
                    "user_id": str(f.user_id),
                    "fact_type": f.fact_type,
                    "label": f.label,
                    "amount": str(f.amount),
                    "currency": f.currency,
                    "source_type": f.source_type,
                    "effective_from": f.effective_from.isoformat(),
                    "effective_to": f.effective_to.isoformat() if f.effective_to else None,
                    "confidence": f.confidence,
                    "source_reference": f.source_reference,
                    "created_at": f.created_at.isoformat() if getattr(f, "created_at", None) else None,
                    "updated_at": f.updated_at.isoformat() if getattr(f, "updated_at", None) else None,
                }
                for f in active_facts
            ],
            "current_period_summary": {
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "income_total": str(summary.income_total),
                "expense_net": str(summary.expense_net),
                "net_cash_flow": str(summary.net_cash_flow),
                "savings_rate": (
                    str(summary.cash_flow_savings_rate)
                    if summary.cash_flow_savings_rate is not None
                    else None
                ),
                "recurring_obligations_monthly": str(summary.recurring_commitments_monthly),
                "available_money_estimate": str(summary.available_money_estimate),
            },
            "active_commitments_count": len(commitments),
            "data_coverage": {
                "days_covered": summary.coverage.days_covered,
                "transaction_count": summary.coverage.transaction_count,
                "coverage_status": summary.coverage.coverage_status,
                "is_complete_month": summary.coverage.is_complete_month,
            },
            "provenance": {
                "engine_version": "1.0.0",
                "rules": "docs/10_FINANCIAL_LOGIC.md",
                "calculation_type": "deterministic_python_decimal",
            },
        }
