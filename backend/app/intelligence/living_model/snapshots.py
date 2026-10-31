"""Profile snapshot management and month-over-month comparison engine.

Ensures idempotent recomputation, immutable periodic records, and transparent period diffs using AsyncSession.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.recurring.amount_analysis import round_money
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.models.financial_fact import ProfileSnapshot


@dataclass
class SnapshotComparisonResult:
    """Month-over-month or period-over-period financial comparison."""

    current_period: str
    previous_period: str
    income_current: Decimal
    income_previous: Decimal
    income_delta: Decimal
    income_percentage_change: Optional[Decimal]
    expense_current: Decimal
    expense_previous: Decimal
    expense_delta: Decimal
    expense_percentage_change: Optional[Decimal]
    net_cash_flow_current: Decimal
    net_cash_flow_previous: Decimal
    net_cash_flow_delta: Decimal
    summary_narrative: str


class SnapshotManager:
    """Manages creation, recomputation, and comparison of profile snapshots."""

    def __init__(self, profile_builder: Optional[ProfileBuilder] = None):
        self.profile_builder = profile_builder or ProfileBuilder()

    async def create_or_update_snapshot(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> ProfileSnapshot:
        """Create or idempotently recompute a ProfileSnapshot for a given period."""
        # Calculate fresh financial summary
        summary = await self.profile_builder.build_summary(
            db, user_id, period_start=period_start, period_end=period_end
        )

        coverage_dict = {
            "days_covered": summary.coverage.days_covered,
            "transaction_count": summary.coverage.transaction_count,
            "account_count": summary.coverage.account_count,
            "is_complete_month": summary.coverage.is_complete_month,
            "coverage_status": summary.coverage.coverage_status,
            "missing_periods_notes": summary.coverage.missing_periods_notes,
        }

        # Check existing snapshot
        stmt = select(ProfileSnapshot).where(
            ProfileSnapshot.user_id == user_id,
            ProfileSnapshot.period_start == period_start,
            ProfileSnapshot.period_end == period_end,
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.snapshot_date = date.today()
            existing.income_total = summary.income_total
            existing.expense_total = summary.expense_net
            existing.net_cash_flow = summary.net_cash_flow
            existing.fixed_cost_estimate = summary.essential_expense_total
            existing.variable_cost_estimate = summary.variable_expense_total
            existing.data_coverage = coverage_dict
            existing.model_version = "1.0.0"
            snapshot = existing
        else:
            snapshot = ProfileSnapshot(
                user_id=user_id,
                snapshot_date=date.today(),
                period_start=period_start,
                period_end=period_end,
                income_total=summary.income_total,
                expense_total=summary.expense_net,
                net_cash_flow=summary.net_cash_flow,
                fixed_cost_estimate=summary.essential_expense_total,
                variable_cost_estimate=summary.variable_expense_total,
                data_coverage=coverage_dict,
                model_version="1.0.0",
            )
            db.add(snapshot)

        await db.commit()
        await db.refresh(snapshot)
        return snapshot

    async def get_user_snapshots(
        self, db: AsyncSession, user_id: uuid.UUID, limit: int = 12
    ) -> List[ProfileSnapshot]:
        """Fetch historical snapshots for a user ordered by period_end descending."""
        stmt = (
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == user_id)
            .order_by(ProfileSnapshot.period_end.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    def compare_snapshots(
        self,
        current_snapshot: ProfileSnapshot,
        previous_snapshot: ProfileSnapshot,
    ) -> SnapshotComparisonResult:
        """Compare two profile snapshots deterministically."""
        inc_curr = current_snapshot.income_total
        inc_prev = previous_snapshot.income_total
        inc_delta = round_money(inc_curr - inc_prev)
        inc_pct: Optional[Decimal] = None
        if inc_prev > Decimal("0.00"):
            inc_pct = round_money((inc_delta / inc_prev) * Decimal("100"))

        exp_curr = current_snapshot.expense_total
        exp_prev = previous_snapshot.expense_total
        exp_delta = round_money(exp_curr - exp_prev)
        exp_pct: Optional[Decimal] = None
        if exp_prev > Decimal("0.00"):
            exp_pct = round_money((exp_delta / exp_prev) * Decimal("100"))

        net_curr = current_snapshot.net_cash_flow
        net_prev = previous_snapshot.net_cash_flow
        net_delta = round_money(net_curr - net_prev)

        curr_period_str = f"{current_snapshot.period_start} to {current_snapshot.period_end}"
        prev_period_str = f"{previous_snapshot.period_start} to {previous_snapshot.period_end}"

        # Generate human-readable narrative
        direction_exp = "increased" if exp_delta > 0 else "decreased"
        narrative = (
            f"Compared to previous period ({prev_period_str}), net spending {direction_exp} "
            f"by ₹{abs(exp_delta)} and net cash flow changed by ₹{net_delta}."
        )

        return SnapshotComparisonResult(
            current_period=curr_period_str,
            previous_period=prev_period_str,
            income_current=inc_curr,
            income_previous=inc_prev,
            income_delta=inc_delta,
            income_percentage_change=inc_pct,
            expense_current=exp_curr,
            expense_previous=exp_prev,
            expense_delta=exp_delta,
            expense_percentage_change=exp_pct,
            net_cash_flow_current=net_curr,
            net_cash_flow_previous=net_prev,
            net_cash_flow_delta=net_delta,
            summary_narrative=narrative,
        )
