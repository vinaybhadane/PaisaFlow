"""User-scoped categorization rule management and match preview."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.category import Category
from backend.app.models.transaction import Transaction


class CategorizationRuleService:
    """Manages creation, preview, and lifecycle of user-defined categorization rules."""

    ALLOWED_SCOPE_TYPES = [
        "exact_merchant",
        "merchant_alias",
        "description_contains",
    ]

    @classmethod
    async def create_rule(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        scope_type: str,
        scope_value: Dict[str, Any],
        subcategory_id: Optional[uuid.UUID] = None,
        priority: int = 100,
        source_transaction_id: Optional[uuid.UUID] = None,
    ) -> CategorizationRule:
        """Create a new user-scoped categorization rule."""
        if scope_type not in cls.ALLOWED_SCOPE_TYPES:
            raise ValidationError(
                f"Invalid scope_type '{scope_type}'. Allowed types: {cls.ALLOWED_SCOPE_TYPES}"
            )

        # Validate category exists
        cat_stmt = select(Category).where(Category.id == category_id)
        cat_res = await session.execute(cat_stmt)
        if not cat_res.scalar_one_or_none():
            raise ValidationError(f"Category '{category_id}' does not exist.")

        if subcategory_id:
            subcat_stmt = select(Category).where(Category.id == subcategory_id)
            subcat_res = await session.execute(subcat_stmt)
            if not subcat_res.scalar_one_or_none():
                raise ValidationError(f"Subcategory '{subcategory_id}' does not exist.")

        rule = CategorizationRule(
            id=uuid.uuid4(),
            user_id=user_id,
            scope_type=scope_type,
            scope_value=scope_value,
            category_id=category_id,
            subcategory_id=subcategory_id,
            priority=priority,
            is_active=True,
            source_transaction_id=source_transaction_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return rule

    @classmethod
    async def list_user_rules(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        active_only: bool = False,
    ) -> List[CategorizationRule]:
        """Fetch all categorization rules belonging to a user ordered by priority."""
        stmt = (
            select(CategorizationRule)
            .where(CategorizationRule.user_id == user_id)
            .order_by(CategorizationRule.priority.desc(), CategorizationRule.created_at.desc())
        )
        if active_only:
            stmt = stmt.where(CategorizationRule.is_active.is_(True))

        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_rule_by_id(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> CategorizationRule:
        """Fetch single rule enforcing user ownership."""
        stmt = select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == user_id,
        )
        res = await session.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            raise NotFoundError(f"Categorization rule '{rule_id}' not found.")
        return rule

    @classmethod
    async def update_rule(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        rule_id: uuid.UUID,
        is_active: Optional[bool] = None,
        priority: Optional[int] = None,
        category_id: Optional[uuid.UUID] = None,
        subcategory_id: Optional[uuid.UUID] = None,
    ) -> CategorizationRule:
        """Update active status, priority, or category mapping of a user rule."""
        rule = await cls.get_rule_by_id(session, user_id, rule_id)

        if is_active is not None:
            rule.is_active = is_active
        if priority is not None:
            rule.priority = priority
        if category_id is not None:
            cat_stmt = select(Category).where(Category.id == category_id)
            cat_res = await session.execute(cat_stmt)
            if not cat_res.scalar_one_or_none():
                raise ValidationError("Specified category_id does not exist.")
            rule.category_id = category_id
            rule.subcategory_id = subcategory_id

        rule.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(rule)
        return rule

    @classmethod
    async def deactivate_rule(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> CategorizationRule:
        """Safely deactivate (undo) a rule without deleting historical provenance."""
        return await cls.update_rule(session, user_id, rule_id, is_active=False)

    @classmethod
    async def preview_rule_matches(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        scope_type: str,
        scope_value: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Preview how many existing user transactions match the proposed rule.

        Does NOT mutate any records.
        """
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        res = await session.execute(stmt)
        transactions = res.scalars().all()

        matching_txs = []
        pattern = ""
        if scope_type == "exact_merchant":
            pattern = str(scope_value.get("merchant_name", "")).upper()
        elif scope_type == "merchant_alias":
            pattern = str(scope_value.get("pattern", "")).upper()
        elif scope_type == "description_contains":
            pattern = str(scope_value.get("substring", "")).upper()

        if pattern:
            for tx in transactions:
                desc = (tx.normalized_description or tx.original_description).upper()
                if pattern in desc:
                    matching_txs.append(
                        {
                            "id": str(tx.id),
                            "date": tx.transaction_date.isoformat(),
                            "description": tx.original_description,
                            "amount": str(tx.amount),
                            "current_category_id": str(tx.category_id) if tx.category_id else None,
                        }
                    )

        return {
            "scope_type": scope_type,
            "scope_value": scope_value,
            "match_count": len(matching_txs),
            "sample_matches": matching_txs[:10],
        }

