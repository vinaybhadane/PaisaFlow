"""Financial fact resolution with effective-dating and precedence hierarchy.

Core rules (from docs/09_AI_INTELLIGENCE_ENGINE.md and docs/10_FINANCIAL_LOGIC.md):
- User-confirmed facts ('user_confirmed') strictly take precedence over
  inferred facts ('transaction_inferred', 'system_calculated').
- Facts maintain effective date ranges (effective_from, effective_to).
- Updating a fact is non-destructive: close the prior fact's effective_to date,
  preserving historical calculation reproducibility.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.financial_fact import FinancialFact


class FinancialFactResolver:
    """Manages and resolves effective-dated financial facts."""

    SOURCE_PRECEDENCE = {
        "user_confirmed": 100,
        "scenario_assumption": 50,
        "transaction_inferred": 30,
        "system_calculated": 20,
    }

    async def create_fact(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        fact_type: str,
        label: str,
        amount: Decimal,
        currency: str = "INR",
        source_type: str = "user_confirmed",
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        confidence: Optional[str] = "high",
        source_reference: Optional[Dict[str, Any]] = None,
    ) -> FinancialFact:
        """Create a new financial fact, handling effective-dating overlaps non-destructively."""
        if amount <= Decimal("0.00"):
            raise ValidationError("Fact amount must be greater than zero.")

        eff_from = effective_from or date.today()

        valid_fact_types = {
            "income",
            "fixed_cost",
            "savings_balance",
            "emergency_target",
            "rent",
            "debt_emi",
            "essential_living",
            "other",
        }
        if fact_type not in valid_fact_types:
            raise ValidationError(
                f"Invalid fact_type '{fact_type}'. Allowed: {sorted(list(valid_fact_types))}"
            )

        if source_type not in self.SOURCE_PRECEDENCE:
            raise ValidationError(
                f"Invalid source_type '{source_type}'. Allowed: {list(self.SOURCE_PRECEDENCE.keys())}"
            )

        # If user_confirmed, close any prior active facts of the same type starting on or before eff_from
        if source_type == "user_confirmed":
            prior_facts_stmt = select(FinancialFact).where(
                FinancialFact.user_id == user_id,
                FinancialFact.fact_type == fact_type,
                FinancialFact.effective_from <= eff_from,
                or_(
                    FinancialFact.effective_to.is_(None),
                    FinancialFact.effective_to >= eff_from,
                ),
            )
            res = await db.execute(prior_facts_stmt)
            prior_facts = list(res.scalars().all())
            for pf in prior_facts:
                if pf.effective_from < eff_from:
                    pf.effective_to = eff_from - timedelta(days=1)
                elif pf.effective_from == eff_from:
                    pf.effective_to = eff_from

        fact = FinancialFact(
            user_id=user_id,
            fact_type=fact_type,
            label=label,
            amount=amount,
            currency=currency,
            source_type=source_type,
            effective_from=eff_from,
            effective_to=effective_to,
            confidence=confidence,
            source_reference=source_reference or {},
        )
        db.add(fact)
        await db.commit()
        await db.refresh(fact)
        return fact

    async def update_fact(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        fact_id: uuid.UUID,
        label: Optional[str] = None,
        amount: Optional[Decimal] = None,
        effective_to: Optional[date] = None,
        confidence: Optional[str] = None,
    ) -> FinancialFact:
        """Update an existing financial fact preserving auditability."""
        stmt = select(FinancialFact).where(
            FinancialFact.id == fact_id,
            FinancialFact.user_id == user_id,
        )
        res = await db.execute(stmt)
        fact = res.scalar_one_or_none()
        if not fact:
            raise NotFoundError(f"Financial fact {fact_id} not found.")

        if label is not None:
            fact.label = label.strip()
        if amount is not None:
            if amount <= Decimal("0.00"):
                raise ValidationError("Amount must be greater than zero.")
            fact.amount = amount
        if effective_to is not None:
            fact.effective_to = effective_to
        if confidence is not None:
            fact.confidence = confidence

        await db.commit()
        await db.refresh(fact)
        return fact

    async def get_active_facts_for_date(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> List[FinancialFact]:
        """Fetch active financial facts as of a specific date, applying source precedence."""
        target_date = as_of_date or date.today()

        stmt = select(FinancialFact).where(
            FinancialFact.user_id == user_id,
            FinancialFact.effective_from <= target_date,
            or_(
                FinancialFact.effective_to.is_(None),
                FinancialFact.effective_to >= target_date,
            ),
        )
        res = await db.execute(stmt)
        all_active = list(res.scalars().all())

        # Group by fact_type and pick the highest precedence fact
        facts_by_type: Dict[str, FinancialFact] = {}
        for fact in all_active:
            existing = facts_by_type.get(fact.fact_type)
            if not existing:
                facts_by_type[fact.fact_type] = fact
            else:
                existing_score = self.SOURCE_PRECEDENCE.get(existing.source_type, 0)
                current_score = self.SOURCE_PRECEDENCE.get(fact.source_type, 0)
                if current_score > existing_score:
                    facts_by_type[fact.fact_type] = fact
                elif current_score == existing_score and fact.effective_from > existing.effective_from:
                    facts_by_type[fact.fact_type] = fact

        return list(facts_by_type.values())

    async def list_all_user_facts(
        self, db: AsyncSession, user_id: uuid.UUID, fact_type: Optional[str] = None
    ) -> List[FinancialFact]:
        """List all facts (active and historical) for a user."""
        stmt = (
            select(FinancialFact)
            .where(FinancialFact.user_id == user_id)
            .order_by(FinancialFact.effective_from.desc())
        )
        if fact_type:
            stmt = stmt.where(FinancialFact.fact_type == fact_type)
        res = await db.execute(stmt)
        return list(res.scalars().all())
