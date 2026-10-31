"""API route handlers for deterministic financial forecasting."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.forecasting.forecaster import FinancialForecaster
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.forecasting import (
    FinancialForecastResponse,
    ForecastMonthItemResponse,
)

router = APIRouter(prefix="/forecast", tags=["Financial Forecast"])
forecaster = FinancialForecaster()


@router.get(
    "",
    response_model=ApiResponse[FinancialForecastResponse],
    summary="Generate deterministic monthly expense and cash flow forecast",
)
async def get_financial_forecast(
    horizon: int = Query(6, ge=1, le=12, description="Forecast horizon in months (1-12)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FinancialForecastResponse]:
    """Generate multi-month deterministic cash flow projections with data coverage disclosure."""
    res = await forecaster.generate_forecast(db, user_id, horizon_months=horizon)

    months_resp = [
        ForecastMonthItemResponse(
            month_index=m.month_index,
            target_month=m.target_month,
            target_month_label=m.target_month_label,
            expected_income=m.expected_income,
            expected_recurring_expenses=m.expected_recurring_expenses,
            expected_variable_expenses=m.expected_variable_expenses,
            expected_total_expenses=m.expected_total_expenses,
            projected_net_cash_flow=m.projected_net_cash_flow,
            projected_cumulative_savings=m.projected_cumulative_savings,
            expected_available_money=m.expected_available_money,
        )
        for m in res.months
    ]

    return ApiResponse(
        data=FinancialForecastResponse(
            generated_date=res.generated_date,
            horizon_months=res.horizon_months,
            currency=res.currency,
            baseline_monthly_income=res.baseline_monthly_income,
            baseline_recurring_expenses=res.baseline_recurring_expenses,
            baseline_variable_expenses=res.baseline_variable_expenses,
            baseline_monthly_expenses=res.baseline_monthly_expenses,
            baseline_net_cash_flow=res.baseline_net_cash_flow,
            data_coverage_status=res.data_coverage_status,
            is_forecastable=res.is_forecastable,
            months=months_resp,
            assumptions=res.assumptions,
            notes=res.notes,
        )
    )

