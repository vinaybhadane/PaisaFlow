"""Pydantic schemas for deterministic financial forecasting."""

from datetime import date
from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field


class ForecastMonthItemResponse(BaseModel):
    """Projected financial position for a future month."""

    month_index: int
    target_month: str
    target_month_label: str
    expected_income: Decimal
    expected_recurring_expenses: Decimal
    expected_variable_expenses: Decimal
    expected_total_expenses: Decimal
    projected_net_cash_flow: Decimal
    projected_cumulative_savings: Decimal
    expected_available_money: Decimal


class FinancialForecastResponse(BaseModel):
    """Consolidated financial forecast result."""

    generated_date: date
    horizon_months: int
    currency: str = "INR"
    baseline_monthly_income: Decimal
    baseline_recurring_expenses: Decimal
    baseline_variable_expenses: Decimal
    baseline_monthly_expenses: Decimal
    baseline_net_cash_flow: Decimal
    data_coverage_status: str
    is_forecastable: bool
    months: List[ForecastMonthItemResponse] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

