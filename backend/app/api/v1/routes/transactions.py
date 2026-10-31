"""API route handlers for transactions, filtering, corrections, and intelligence provenance."""

from datetime import date, datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.dependencies import get_current_user_id
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.db.dependencies import get_db
from backend.app.intelligence.corrections.correction_service import (
    TransactionCorrectionService,
)
from backend.app.intelligence.corrections.learning_rules import (
    CategorizationRuleService,
)
from backend.app.intelligence.engine import TransactionIntelligenceEngine
from backend.app.intelligence.explanations.explanation_service import (
    TransactionExplanationService,
)
from backend.app.models.transaction import Transaction
from backend.app.schemas.categorization_rule import (
    CategorizationRuleResponse,
    RulePreviewResponse,
)
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.transaction import (
    BulkCategorizeRequest,
    BulkCategorizeResponse,
    PaginatedTransactionsResponse,
    TransactionExplanationResponse,
    TransactionResponse,
    TransactionUpdateRequest,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])
engine = TransactionIntelligenceEngine()


class RuleCreationWrapper(BaseModel):
    """Payload for creating or previewing a rule derived from an existing transaction."""

    category_id: Optional[uuid.UUID] = None
    scope_type: str = "exact_merchant"
    scope_value: Optional[Dict[str, Any]] = None
    priority: int = 150
    preview_only: bool = False


@router.get(
    "",
    response_model=ApiResponse[PaginatedTransactionsResponse],
    summary="List transactions with multi-criteria filtering and pagination",
)
async def list_transactions(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: expense, income, transfer, refund"),
    merchant_id: Optional[uuid.UUID] = Query(None, description="Filter by merchant ID"),
    review_status: Optional[str] = Query(None, description="Filter by status: confirmed, flagged, corrected"),
    search: Optional[str] = Query(None, description="Search keyword in description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedTransactionsResponse]:
    """Retrieve user transactions with pagination and rich filters."""
    base_query = select(Transaction).where(Transaction.user_id == user_id)

    if from_date:
        base_query = base_query.where(Transaction.transaction_date >= from_date)
    if to_date:
        base_query = base_query.where(Transaction.transaction_date <= to_date)
    if category_id:
        base_query = base_query.where(Transaction.category_id == category_id)
    if transaction_type:
        base_query = base_query.where(Transaction.transaction_type == transaction_type)
    if merchant_id:
        base_query = base_query.where(Transaction.merchant_id == merchant_id)
    if review_status:
        base_query = base_query.where(Transaction.review_status == review_status)
    if search and search.strip():
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            Transaction.original_description.ilike(term)
            | Transaction.normalized_description.ilike(term)
        )

    # Count total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        base_query.options(
            selectinload(Transaction.category),
            selectinload(Transaction.merchant),
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    transactions = res.scalars().all()

    items: List[TransactionResponse] = [
        TransactionResponse(
            id=tx.id,
            user_id=tx.user_id,
            account_id=tx.account_id,
            import_batch_id=tx.import_batch_id,
            transaction_date=tx.transaction_date,
            posted_date=tx.posted_date,
            original_description=tx.original_description,
            normalized_description=tx.normalized_description,
            merchant_id=tx.merchant_id,
            merchant_name=tx.merchant.canonical_name if tx.merchant else None,
            amount=tx.amount,
            currency=tx.currency,
            direction=tx.direction,
            transaction_type=tx.transaction_type,
            category_id=tx.category_id,
            category_name=tx.category.name if tx.category else None,
            subcategory_id=tx.subcategory_id,
            subcategory_name=None,
            categorization_method=tx.categorization_method,
            confidence=tx.confidence,
            review_status=tx.review_status,
            duplicate_fingerprint=tx.duplicate_fingerprint,
            is_excluded=tx.is_excluded,
            created_at=tx.created_at,
        )
        for tx in transactions
    ]

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return ApiResponse(
        data=PaginatedTransactionsResponse(
            items=items,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get(
    "/{transaction_id}",
    response_model=ApiResponse[TransactionExplanationResponse],
    summary="Get transaction detail and explainability provenance",
)
async def get_transaction_detail(
    transaction_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TransactionExplanationResponse]:
    """Retrieve full transaction details with confidence evidence and correction history."""
    explanation = await TransactionExplanationService.get_explanation(
        session=db,
        user_id=user_id,
        transaction_id=transaction_id,
    )
    return ApiResponse(
        data=TransactionExplanationResponse(
            transaction_id=explanation.transaction_id,
            original_description=explanation.original_description,
            normalized_description=explanation.normalized_description,
            merchant_name=explanation.merchant_name,
            category_id=explanation.category_id,
            category_name=explanation.category_name,
            subcategory_id=explanation.subcategory_id,
            subcategory_name=explanation.subcategory_name,
            confidence_level=explanation.confidence_level,
            confidence_score=explanation.confidence_score,
            classification_method=explanation.classification_method,
            review_status=explanation.review_status,
            is_excluded=explanation.is_excluded,
            evidence_reasons=explanation.evidence_reasons,
            corrections_history=explanation.corrections_history,
        )
    )


@router.patch(
    "/{transaction_id}",
    response_model=ApiResponse[TransactionResponse],
    summary="Correct transaction category and record audit provenance",
)
async def correct_transaction(
    transaction_id: uuid.UUID,
    request: TransactionUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TransactionResponse]:
    """Apply an explicit user category correction without modifying monetary values or transaction date."""
    if request.category_id is not None:
        tx = await TransactionCorrectionService.correct_transaction(
            session=db,
            user_id=user_id,
            transaction_id=transaction_id,
            category_id=request.category_id,
            subcategory_id=request.subcategory_id,
            apply_future_rule=request.apply_future_rule,
            scope_type=request.scope_type,
        )
    else:
        # Simple review status update
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        res = await db.execute(stmt)
        tx = res.scalar_one_or_none()
        if not tx:
            raise NotFoundError(f"Transaction '{transaction_id}' not found.")

        if request.review_status:
            tx.review_status = request.review_status
            tx.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(tx)

    # Reload relationships for response
    rel_stmt = (
        select(Transaction)
        .where(Transaction.id == tx.id)
        .options(
            selectinload(Transaction.category),
            selectinload(Transaction.merchant),
        )
    )
    rel_res = await db.execute(rel_stmt)
    loaded_tx = rel_res.scalar_one()

    return ApiResponse(
        data=TransactionResponse(
            id=loaded_tx.id,
            user_id=loaded_tx.user_id,
            account_id=loaded_tx.account_id,
            import_batch_id=loaded_tx.import_batch_id,
            transaction_date=loaded_tx.transaction_date,
            posted_date=loaded_tx.posted_date,
            original_description=loaded_tx.original_description,
            normalized_description=loaded_tx.normalized_description,
            merchant_id=loaded_tx.merchant_id,
            merchant_name=loaded_tx.merchant.canonical_name if loaded_tx.merchant else None,
            amount=loaded_tx.amount,
            currency=loaded_tx.currency,
            direction=loaded_tx.direction,
            transaction_type=loaded_tx.transaction_type,
            category_id=loaded_tx.category_id,
            category_name=loaded_tx.category.name if loaded_tx.category else None,
            subcategory_id=loaded_tx.subcategory_id,
            subcategory_name=None,
            categorization_method=loaded_tx.categorization_method,
            confidence=loaded_tx.confidence,
            review_status=loaded_tx.review_status,
            duplicate_fingerprint=loaded_tx.duplicate_fingerprint,
            is_excluded=loaded_tx.is_excluded,
            created_at=loaded_tx.created_at,
        )
    )


@router.post(
    "/{transaction_id}/correction-rule",
    summary="Create future categorization rule from transaction or preview matches",
)
async def create_correction_rule(
    transaction_id: uuid.UUID,
    request: RuleCreationWrapper,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[Any]:
    """Synthesize a reusable categorization rule from an existing transaction or preview its matches."""
    stmt = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()
    if not tx:
        raise NotFoundError(f"Transaction '{transaction_id}' not found.")

    pattern = (tx.normalized_description or tx.original_description).strip()
    scope_value = request.scope_value or {
        "merchant_name": pattern,
        "pattern": pattern,
        "substring": pattern,
    }

    if request.preview_only:
        preview = await CategorizationRuleService.preview_rule_matches(
            session=db,
            user_id=user_id,
            scope_type=request.scope_type,
            scope_value=scope_value,
        )
        return ApiResponse(data=RulePreviewResponse(**preview))

    target_category_id = request.category_id or tx.category_id
    if not target_category_id:
        raise ValidationError("Target category_id must be provided to create a rule.")

    rule = await CategorizationRuleService.create_rule(
        session=db,
        user_id=user_id,
        category_id=target_category_id,
        scope_type=request.scope_type,
        scope_value=scope_value,
        priority=request.priority,
        source_transaction_id=tx.id,
    )
    return ApiResponse(data=CategorizationRuleResponse.model_validate(rule))


@router.post(
    "/bulk-categorize",
    response_model=ApiResponse[BulkCategorizeResponse],
    summary="Execute bulk categorization across unassigned or pending transactions",
)
async def bulk_categorize_transactions(
    request: BulkCategorizeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkCategorizeResponse]:
    """Run transaction intelligence engine across user's transaction records."""
    summary = await engine.bulk_categorize(
        session=db,
        user_id=user_id,
        transaction_ids=request.transaction_ids,
        reapply_confirmed=request.reapply_confirmed,
    )
    return ApiResponse(data=BulkCategorizeResponse(**summary))
