"""Pydantic schemas for user-defined categorization rules and corrections."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CategorizationRuleCreateRequest(BaseModel):
    """Payload to create a new user categorization rule."""

    category_id: uuid.UUID
    subcategory_id: Optional[uuid.UUID] = None
    scope_type: str = Field(
        ...,
        description="'exact_merchant', 'merchant_alias', or 'description_contains'",
    )
    scope_value: Dict[str, Any] = Field(
        ...,
        description="Configuration dictionary, e.g. {'merchant_name': 'Swiggy'}",
    )
    priority: int = 100
    source_transaction_id: Optional[uuid.UUID] = None


class CategorizationRuleUpdateRequest(BaseModel):
    """Payload to update an existing categorization rule."""

    is_active: Optional[bool] = None
    priority: Optional[int] = None
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None


class CategorizationRuleResponse(BaseModel):
    """Representation of a user categorization rule."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    scope_type: str
    scope_value: Dict[str, Any]
    category_id: uuid.UUID
    subcategory_id: Optional[uuid.UUID] = None
    priority: int
    is_active: bool
    source_transaction_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class RulePreviewResponse(BaseModel):
    """Preview of existing transactions matching a proposed rule."""

    scope_type: str
    scope_value: Dict[str, Any]
    match_count: int
    sample_matches: List[Dict[str, Any]] = []


class TransactionCorrectionResponse(BaseModel):
    """Audit log item representing a user correction."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    transaction_id: uuid.UUID
    field_name: str
    old_value: Dict[str, Any]
    new_value: Dict[str, Any]
    rule_id: Optional[uuid.UUID] = None
    created_at: datetime
    reverted_at: Optional[datetime] = None
