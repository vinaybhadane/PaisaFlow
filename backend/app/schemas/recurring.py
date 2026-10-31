"""Pydantic schemas for recurring commitments, observations, and price changes."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class RecurringObservationResponse(BaseModel):
    """Historical observation supporting a recurring commitment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commitment_id: uuid.UUID
    transaction_id: uuid.UUID
    observed_amount: Decimal
    observed_date: date
    created_at: datetime


class PriceChangeEventResponse(BaseModel):
    """Price change event for a recurring commitment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commitment_id: uuid.UUID
    previous_amount: Decimal
    new_amount: Decimal
    absolute_change: Decimal
    percentage_change: Decimal
    detected_at: datetime
    evidence: Optional[Dict[str, Any]] = None
    status: str


class RecurringCommitmentResponse(BaseModel):
    """Recurring commitment summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    merchant_id: Optional[uuid.UUID] = None
    display_name: str
    cadence: str
    estimated_cadence_days: Optional[int] = None
    typical_amount: Decimal
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    currency: str = "INR"
    confidence: str
    status: str
    last_observed_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    evidence: Optional[Dict[str, Any]] = None
    monthly_equivalent: Optional[Decimal] = None
    estimated_annual_cost: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


class RecurringCommitmentDetailResponse(RecurringCommitmentResponse):
    """Recurring commitment with observations and price change history."""

    observations: List[RecurringObservationResponse] = Field(default_factory=list)
    price_changes: List[PriceChangeEventResponse] = Field(default_factory=list)


class CommitmentReviewRequest(BaseModel):
    """Request payload for reviewing a detected commitment."""

    action: str = Field(
        ...,
        description="Action to apply: 'confirm', 'reject', or 'review_required'",
        examples=["confirm", "reject", "review_required"],
    )


class CommitmentUpdateRequest(BaseModel):
    """Request payload for updating editable commitment fields."""

    display_name: Optional[str] = None
    cadence: Optional[str] = None
    typical_amount: Optional[Decimal] = None
    status: Optional[str] = None

