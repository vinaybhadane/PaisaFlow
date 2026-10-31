"""User transaction correction service preserving immutable financial data and audit history."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.intelligence.corrections.learning_rules import CategorizationRuleService
from backend.app.models.category import Category
from backend.app.models.transaction import Transaction
from backend.app.models.transaction_correction import TransactionCorrection


class TransactionCorrectionService:
    """Manages transaction category corrections and reversible audit tracking."""

    @classmethod
    async def correct_transaction(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        category_id: uuid.UUID,
        subcategory_id: Optional[uuid.UUID] = None,
        apply_future_rule: bool = False,
        scope_type: str = "exact_merchant",
    ) -> Transaction:
        """Apply a user correction to a transaction's category while preserving immutable financial facts."""
        # 1. Fetch transaction ensuring ownership
        tx_stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        tx_res = await session.execute(tx_stmt)
        tx = tx_res.scalar_one_or_none()
        if not tx:
            raise NotFoundError(f"Transaction '{transaction_id}' not found.")

        # 2. Validate target category
        cat_stmt = select(Category).where(Category.id == category_id)
        cat_res = await session.execute(cat_stmt)
        category = cat_res.scalar_one_or_none()
        if not category:
            raise ValidationError(f"Category '{category_id}' does not exist.")

        if subcategory_id:
            subcat_stmt = select(Category).where(Category.id == subcategory_id)
            subcat_res = await session.execute(subcat_stmt)
            if not subcat_res.scalar_one_or_none():
                raise ValidationError(f"Subcategory '{subcategory_id}' does not exist.")

        # 3. Snapshot previous values for explainable audit
        old_value = {
            "category_id": str(tx.category_id) if tx.category_id else None,
            "subcategory_id": str(tx.subcategory_id) if tx.subcategory_id else None,
            "categorization_method": tx.categorization_method,
            "confidence": tx.confidence,
            "review_status": tx.review_status,
        }

        new_value = {
            "category_id": str(category_id),
            "category_name": category.name,
            "subcategory_id": str(subcategory_id) if subcategory_id else None,
            "categorization_method": "user_correction",
            "confidence": "high",
        }

        # 4. Optional future learning rule synthesis
        created_rule_id: Optional[uuid.UUID] = None
        if apply_future_rule:
            rule_pattern = (tx.normalized_description or tx.original_description).strip()
            rule = await CategorizationRuleService.create_rule(
                session=session,
                user_id=user_id,
                category_id=category_id,
                subcategory_id=subcategory_id,
                scope_type=scope_type,
                scope_value={"merchant_name": rule_pattern, "pattern": rule_pattern, "substring": rule_pattern},
                priority=150,  # User explicit corrections take highest precedence
                source_transaction_id=tx.id,
            )
            created_rule_id = rule.id

        # 5. Persist correction audit record
        correction = TransactionCorrection(
            id=uuid.uuid4(),
            user_id=user_id,
            transaction_id=tx.id,
            field_name="category_id",
            old_value=old_value,
            new_value=new_value,
            rule_id=created_rule_id,
            created_at=datetime.now(timezone.utc),
        )
        session.add(correction)

        # 6. Update transaction category (preserving immutable amount, date, direction)
        tx.category_id = category_id
        tx.subcategory_id = subcategory_id
        tx.categorization_method = "user_correction"
        tx.confidence = "high"
        tx.review_status = "corrected"
        tx.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(tx)
        return tx

    @classmethod
    async def revert_correction(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        correction_id: uuid.UUID,
    ) -> Transaction:
        """Revert a historical correction back to its previous state."""
        corr_stmt = select(TransactionCorrection).where(
            TransactionCorrection.id == correction_id,
            TransactionCorrection.user_id == user_id,
        )
        corr_res = await session.execute(corr_stmt)
        correction = corr_res.scalar_one_or_none()
        if not correction:
            raise NotFoundError(f"Correction '{correction_id}' not found.")

        if correction.reverted_at:
            raise ValidationError("This correction has already been reverted.")

        # Fetch transaction
        tx_stmt = select(Transaction).where(
            Transaction.id == correction.transaction_id,
            Transaction.user_id == user_id,
        )
        tx_res = await session.execute(tx_stmt)
        tx = tx_res.scalar_one_or_none()
        if not tx:
            raise NotFoundError("Associated transaction not found.")

        # Revert fields
        prev_cat_id_raw = correction.old_value.get("category_id")
        prev_subcat_id_raw = correction.old_value.get("subcategory_id")

        tx.category_id = uuid.UUID(prev_cat_id_raw) if prev_cat_id_raw else None
        tx.subcategory_id = uuid.UUID(prev_subcat_id_raw) if prev_subcat_id_raw else None
        tx.categorization_method = correction.old_value.get("categorization_method", "reverted")
        tx.confidence = correction.old_value.get("confidence", "medium")
        tx.review_status = "confirmed"
        tx.updated_at = datetime.now(timezone.utc)

        correction.reverted_at = datetime.now(timezone.utc)

        # Deactivate associated rule if one was created
        if correction.rule_id:
            await CategorizationRuleService.deactivate_rule(session, user_id, correction.rule_id)

        await session.commit()
        await session.refresh(tx)
        return tx

    @classmethod
    async def list_corrections_for_transaction(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> List[TransactionCorrection]:
        """Fetch audit trail of all corrections applied to a specific transaction."""
        stmt = (
            select(TransactionCorrection)
            .where(
                TransactionCorrection.transaction_id == transaction_id,
                TransactionCorrection.user_id == user_id,
            )
            .order_by(TransactionCorrection.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

