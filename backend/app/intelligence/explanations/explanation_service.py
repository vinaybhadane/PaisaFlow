"""Explanation and provenance generation for transaction classifications."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.models.transaction import Transaction
from backend.app.models.transaction_correction import TransactionCorrection


@dataclass
class TransactionExplanation:
    """Comprehensive explainability payload for a categorized transaction."""

    transaction_id: uuid.UUID
    original_description: str
    normalized_description: str
    merchant_name: Optional[str]
    category_id: Optional[uuid.UUID]
    category_name: Optional[str]
    subcategory_id: Optional[uuid.UUID]
    subcategory_name: Optional[str]
    confidence_level: str
    confidence_score: Optional[float]
    classification_method: str
    review_status: str
    is_excluded: bool
    evidence_reasons: List[str] = field(default_factory=list)
    corrections_history: List[Dict[str, Any]] = field(default_factory=list)


class TransactionExplanationService:
    """Produces explainable provenance records for transaction review."""

    @classmethod
    async def get_explanation(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> TransactionExplanation:
        """Fetch transaction with category, merchant, and correction audit history."""
        stmt = (
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .options(
                selectinload(Transaction.category),
                selectinload(Transaction.merchant),
            )
        )
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()
        if not tx:
            raise NotFoundError(f"Transaction '{transaction_id}' not found.")

        # Fetch corrections audit
        corr_stmt = (
            select(TransactionCorrection)
            .where(
                TransactionCorrection.transaction_id == tx.id,
                TransactionCorrection.user_id == user_id,
            )
            .order_by(TransactionCorrection.created_at.desc())
        )
        corr_res = await session.execute(corr_stmt)
        corrections = corr_res.scalars().all()

        corrections_list = [
            {
                "id": str(c.id),
                "field_name": c.field_name,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "created_at": c.created_at.isoformat(),
                "reverted_at": c.reverted_at.isoformat() if c.reverted_at else None,
            }
            for c in corrections
        ]

        # Determine evidence reasons
        evidence: List[str] = []
        method = tx.categorization_method or "unknown"
        if method == "user_correction":
            evidence.append("User manually corrected this transaction's category.")
        elif method == "user_rule":
            evidence.append("Categorized according to custom user-defined rule.")
        elif method == "deterministic_transfer":
            evidence.append("Internal account transfer excluded from consolidated spending.")
        elif method == "deterministic_refund":
            evidence.append("Refund adjustment recorded against source credit.")
        elif "merchant" in method:
            evidence.append(f"Mapped via resolved merchant '{tx.merchant.canonical_name if tx.merchant else 'Merchant'}'.")
        else:
            evidence.append(f"Classified using engine method: '{method}'.")

        if tx.is_excluded:
            evidence.append("Excluded from consolidated income and expense totals.")

        category_name = tx.category.name if tx.category else None

        # Parse confidence score
        conf_score: Optional[float] = None
        if tx.confidence:
            try:
                conf_score = float(tx.confidence)
            except ValueError:
                conf_score = 0.95 if tx.confidence == "high" else (0.70 if tx.confidence == "medium" else 0.40)

        return TransactionExplanation(
            transaction_id=tx.id,
            original_description=tx.original_description,
            normalized_description=tx.normalized_description,
            merchant_name=tx.merchant.canonical_name if tx.merchant else None,
            category_id=tx.category_id,
            category_name=category_name,
            subcategory_id=tx.subcategory_id,
            subcategory_name=None,
            confidence_level=tx.confidence or "medium",
            confidence_score=conf_score,
            classification_method=method,
            review_status=tx.review_status,
            is_excluded=tx.is_excluded,
            evidence_reasons=evidence,
            corrections_history=corrections_list,
        )

