"""Pydantic schemas for transactions, filtering, correction, and explainability."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TransactionResponse(BaseModel):
    """Complete financial transaction representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID
    import_batch_id: Optional[uuid.UUID] = None
    transaction_date: date
    posted_date: Optional[date] = None
    original_description: str
    normalized_description: str
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    amount: Decimal
    currency: str = "INR"
    direction: str
    transaction_type: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    subcategory_id: Optional[uuid.UUID] = None
    subcategory_name: Optional[str] = None
    categorization_method: Optional[str] = None
    confidence: Optional[str] = None
    review_status: str
    duplicate_fingerprint: Optional[str] = None
    is_excluded: bool = False
    created_at: datetime


class PaginatedTransactionsResponse(BaseModel):
    """Paginated list of transactions."""

    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionUpdateRequest(BaseModel):
    """Safe editable fields for transaction correction."""

    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    review_status: Optional[str] = None
    apply_future_rule: bool = Field(
        False,
        description="Whether to create a persistent future rule for this merchant/pattern.",
    )
    scope_type: str = Field(
        "exact_merchant",
        description="Rule scope: 'exact_merchant', 'merchant_alias', or 'description_contains'",
    )


class TransactionExplanationResponse(BaseModel):
    """Explainable intelligence provenance for a single transaction."""

    transaction_id: uuid.UUID
    original_description: str
    normalized_description: str
    merchant_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    subcategory_id: Optional[uuid.UUID] = None
    subcategory_name: Optional[str] = None
    confidence_level: str
    confidence_score: Optional[float] = None
    classification_method: str
    review_status: str
    is_excluded: bool
    evidence_reasons: List[str] = []
    corrections_history: List[Dict[str, Any]] = []


class BulkCategorizeRequest(BaseModel):
    """Payload to trigger batch categorization on pending transactions."""

    transaction_ids: Optional[List[uuid.UUID]] = None
    reapply_confirmed: bool = False


class BulkCategorizeResponse(BaseModel):
    """Summary counts from bulk categorization execution."""

    total_evaluated: int
    categorized_count: int
    review_required_count: int
    uncategorized_count: int
