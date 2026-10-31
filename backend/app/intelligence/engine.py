"""Transaction Intelligence Engine coordinating merchant resolution, categorization, and bulk execution."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.categorization.classifier import (
    ClassificationResult,
    TransactionClassifier,
)
from backend.app.intelligence.categorization.taxonomy import CategoryTaxonomyService
from backend.app.intelligence.corrections.learning_rules import CategorizationRuleService
from backend.app.intelligence.merchant.enrichment import MerchantEnrichmentService
from backend.app.intelligence.merchant.resolver import MerchantResolver
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.category import Category
from backend.app.models.transaction import Transaction


class TransactionIntelligenceEngine:
    """Core transaction intelligence coordinator for categorization and merchant resolution."""

    def __init__(self) -> None:
        self.merchant_resolver = MerchantResolver()
        self.classifier = TransactionClassifier(merchant_resolver=self.merchant_resolver)

    async def process_transaction(
        self,
        session: AsyncSession,
        transaction: Transaction,
        user_rules: Optional[List[CategorizationRule]] = None,
        cached_categories: Optional[Dict[str, Category]] = None,
    ) -> ClassificationResult:
        """Categorize a single transaction and attach resolved merchant entity."""
        result = await self.classifier.classify(
            session=session,
            user_id=transaction.user_id,
            normalized_description=transaction.normalized_description or transaction.original_description,
            direction=transaction.direction,
            transaction_type=transaction.transaction_type,
            user_rules=user_rules,
            cached_categories=cached_categories,
        )

        # Link merchant entity if canonical merchant resolved
        if result.resolved_merchant_name:
            merchant = await MerchantEnrichmentService.get_or_create_merchant(
                session=session,
                canonical_name=result.resolved_merchant_name,
                category_id=result.category_id,
            )
            transaction.merchant_id = merchant.id

        # Update transaction categorization fields
        transaction.category_id = result.category_id
        transaction.subcategory_id = result.subcategory_id
        transaction.categorization_method = result.resolution_method
        transaction.confidence = result.confidence.level
        transaction.review_status = result.review_status
        transaction.updated_at = datetime.now(timezone.utc)

        return result

    async def bulk_categorize(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_ids: Optional[List[uuid.UUID]] = None,
        reapply_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Perform high-performance bulk categorization across user transactions without N+1 query overhead."""
        # 1. Preload static taxonomy and user-specific rules once
        cached_categories = await CategoryTaxonomyService.seed_system_categories(session)
        user_rules = await CategorizationRuleService.list_user_rules(session, user_id, active_only=True)

        # 2. Query target transactions
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if transaction_ids:
            stmt = stmt.where(Transaction.id.in_(transaction_ids))
        elif not reapply_confirmed:
            # Only process unassigned, pending, or flagged transactions
            stmt = stmt.where(
                (Transaction.category_id.is_(None)) | (Transaction.review_status != "confirmed")
            )

        res = await session.execute(stmt)
        transactions = res.scalars().all()

        total = len(transactions)
        categorized = 0
        review_required = 0
        uncategorized = 0

        for tx in transactions:
            # Skip user-corrected transactions unless explicitly requested
            if tx.categorization_method == "user_correction" and not reapply_confirmed:
                continue

            result = await self.process_transaction(
                session=session,
                transaction=tx,
                user_rules=user_rules,
                cached_categories=cached_categories,
            )

            if result.category_name == "Other" and result.subcategory_name == "Uncategorized Expense":
                uncategorized += 1
                review_required += 1
            elif result.review_status == "flagged" or result.confidence.requires_review:
                review_required += 1
                categorized += 1
            else:
                categorized += 1

        await session.commit()

        return {
            "total_evaluated": total,
            "categorized_count": categorized,
            "review_required_count": review_required,
            "uncategorized_count": uncategorized,
        }

