"""Pydantic schemas for financial insights, category spending, and monthly trends."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class FinancialInsightResponse(BaseModel):
    """Structured financial insight with provenance."""

    insight_type: str
    title: str
    explanation: str
    metric_value: str
    change_percentage: Optional[Decimal] = None
    period: str
    confidence: str
    severity: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class CategorySpendingItemResponse(BaseModel):
    """Category spending breakdown item."""

    category_id: Optional[uuid.UUID] = None
    category_name: str
    current_spend: Decimal
    previous_spend: Decimal
    change_amount: Decimal
    change_percentage: Optional[Decimal] = None
    spend_percentage: Decimal
    is_essential: bool
    trend: str


class MerchantSpendingItemResponse(BaseModel):
    """Merchant spending concentration item."""

    merchant_name: str
    merchant_id: Optional[uuid.UUID] = None
    total_amount: Decimal
    transaction_count: int
    percentage_of_total: Decimal


class CategorySpendingResponse(BaseModel):
    """Consolidated category-wise spending analysis."""

    period_start: date
    period_end: date
    currency: str = "INR"
    total_gross_expense: Decimal
    total_refunds: Decimal
    total_net_expense: Decimal
    essential_spend: Decimal
    discretionary_spend: Decimal
    essential_percentage: Decimal
    discretionary_percentage: Decimal
    categories: List[CategorySpendingItemResponse]
    top_merchants: List[MerchantSpendingItemResponse]


class MonthlyTrendItemResponse(BaseModel):
    """Historical monthly cash flow and spending trend."""

    month_key: str
    month_label: str
    period_start: date
    period_end: date
    income_total: Decimal
    total_spend: Decimal
    essential_spend: Decimal
    variable_spend: Decimal
    net_cash_flow: Decimal
