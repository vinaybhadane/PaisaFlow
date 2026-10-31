"""Pydantic schemas for what-if scenarios and simulations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ScenarioRunRequest(BaseModel):
    """Payload to execute an on-demand what-if scenario."""

    scenario_type: str = Field(
        ...,
        description="Type of what-if scenario",
        examples=[
            "reduce_category_percentage",
            "reduce_category_fixed",
            "cancel_recurring",
            "income_change",
            "add_expense",
            "custom_savings",
        ],
    )
    input_parameters: Dict[str, Any] = Field(
        ...,
        description="Parameters specific to the scenario (reduction_percentage, amount, etc.)",
        examples=[{"reduction_percentage": "25", "category_name": "Food"}],
    )
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    goal_id: Optional[uuid.UUID] = None


class ScenarioPeriodImpactsResponse(BaseModel):
    """Cumulative impact across standard horizons."""

    monthly_delta: Decimal
    three_month_impact: Decimal
    six_month_impact: Decimal
    twelve_month_impact: Decimal


class SimulationRunResponse(BaseModel):
    """Result of running a what-if simulation."""

    scenario_type: str
    title: str
    currency: str = "INR"
    baseline: Dict[str, Any]
    scenario: Dict[str, Any]
    delta: Dict[str, Any]
    period_impacts: ScenarioPeriodImpactsResponse
    assumptions: List[str]
    notes: List[str]
    calculation_version: str = "1.0.0"


class ScenarioCreateRequest(BaseModel):
    """Payload to save a what-if simulation scenario."""

    title: str = Field(..., max_length=255, examples=["Reduce Dining Spend by 25%"])
    scenario_type: str = Field(..., max_length=64)
    input_parameters: Dict[str, Any]
    baseline_result: Dict[str, Any]
    scenario_result: Dict[str, Any]
    assumptions: Dict[str, Any]
    calculation_version: str = "1.0.0"


class ScenarioUpdateRequest(BaseModel):
    """Payload to update saved scenario attributes."""

    title: Optional[str] = Field(default=None, max_length=255)


class ScenarioResponse(BaseModel):
    """Saved scenario representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    scenario_type: str
    input_parameters: Dict[str, Any]
    baseline_result: Dict[str, Any]
    scenario_result: Dict[str, Any]
    assumptions: Dict[str, Any]
    calculation_version: str
    created_at: datetime


class ScenarioCompareRequest(BaseModel):
    """Payload to compare multiple saved scenarios."""

    scenario_ids: List[uuid.UUID] = Field(..., min_length=1)


class ScenarioComparisonItem(BaseModel):
    """Individual scenario in comparison view."""

    id: str
    title: str
    scenario_type: str
    monthly_delta: str
    twelve_month_impact: str
    updated_savings_rate: str


class ScenarioComparisonResponse(BaseModel):
    """Side-by-side comparison of multiple scenarios."""

    user_id: uuid.UUID
    scenario_count: int
    scenarios: List[ScenarioComparisonItem]

