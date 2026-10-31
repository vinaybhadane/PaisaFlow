"""Pydantic schemas for the Living Money Model, financial facts, summaries, and snapshots."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class FinancialFactCreateRequest(BaseModel):
    """Payload to create or confirm a financial fact."""

    fact_type: str = Field(
        ...,
        description="Type of financial fact: income, fixed_cost, savings_balance, emergency_target, rent, debt_emi, other",
        examples=["rent", "income", "fixed_cost"],
    )
    label: str = Field(..., max_length=255, examples=["Monthly Apartment Rent"])
    amount: Decimal = Field(..., gt=Decimal("0.00"), examples=[Decimal("25000.00")])
    currency: str = Field(default="INR", max_length=3)
    source_type: str = Field(default="user_confirmed")
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    confidence: Optional[str] = "high"
    source_reference: Optional[Dict[str, Any]] = None


class FinancialFactUpdateRequest(BaseModel):
    """Payload to update an existing financial fact."""

    label: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    effective_to: Optional[date] = None
    confidence: Optional[str] = None


class FinancialFactResponse(BaseModel):
    """Financial fact representation with provenance and effective dates."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    fact_type: str
    label: str
    amount: Decimal
    currency: str = "INR"
    source_type: str
    effective_from: date
    effective_to: Optional[date] = None
    confidence: Optional[str] = None
    source_reference: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DataCoverageResponse(BaseModel):
    """Data coverage metrics."""

    days_covered: int
    transaction_count: int
    account_count: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    is_complete_month: bool
    coverage_status: str
    missing_periods_notes: List[str] = Field(default_factory=list)


class FinancialSummaryResponse(BaseModel):
    """Deterministic financial summary following docs/10_FINANCIAL_LOGIC.md."""

    period_start: date
    period_end: date
    currency: str = "INR"
    income_total: Decimal
    expense_gross: Decimal
    refunds_total: Decimal
    expense_net: Decimal
    transfers_excluded_total: Decimal
    transfers_excluded_count: int
    net_cash_flow: Decimal
    cash_flow_savings_rate: Optional[Decimal] = None
    essential_expense_total: Decimal
    variable_expense_total: Decimal
    recurring_commitments_monthly: Decimal
    available_money_estimate: Decimal
    coverage: DataCoverageResponse
    notes: List[str] = Field(default_factory=list)


class LivingProfileResponse(BaseModel):
    """Living Money Model aggregate profile."""

    user_id: uuid.UUID
    as_of_date: date
    active_facts: List[FinancialFactResponse] = Field(default_factory=list)
    current_period_summary: Dict[str, Any]
    active_commitments_count: int
    data_coverage: Dict[str, Any]
    provenance: Dict[str, Any]


class ProfileSnapshotResponse(BaseModel):
    """Immutable periodic snapshot of user financial profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    snapshot_date: date
    period_start: date
    period_end: date
    income_total: Decimal
    expense_total: Decimal
    net_cash_flow: Decimal
    fixed_cost_estimate: Decimal
    variable_cost_estimate: Decimal
    data_coverage: Dict[str, Any]
    model_version: str
    created_at: datetime


class SnapshotRecomputeRequest(BaseModel):
    """Request to recompute a periodic profile snapshot."""

    period_start: date
    period_end: date


class DemoPersonaResponse(BaseModel):
    """Synthetic persona representation for demo exploration."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str
    email: Optional[str] = None
    persona_key: str
    profile_label: str
    is_synthetic: bool = True
