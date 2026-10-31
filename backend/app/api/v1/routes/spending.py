"""API route handlers for category spending breakdown, concentration, and historical trends."""

from datetime import date
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.insights.spending_analyzer import SpendingAnalyzer
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.insights import (
    CategorySpendingItemResponse,
    CategorySpendingResponse,
    MerchantSpendingItemResponse,
    MonthlyTrendItemResponse,
)

router = APIRouter(prefix="/spending", tags=["Spending Analysis"])
analyzer = SpendingAnalyzer()


@router.get(
    "/categories",
    response_model=ApiResponse[CategorySpendingResponse],
    summary="Get category-wise spend distribution and prior period comparisons",
)
async def get_category_spending(
    period_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategorySpendingResponse]:
    """Retrieve category spending breakdown with essential vs discretionary classification."""
    res = await analyzer.analyze_period_spending(
        db, user_id, period_start=period_start, period_end=period_end
    )
    categories_resp = [
        CategorySpendingItemResponse(
            category_id=c.category_id,
            category_name=c.category_name,
            current_spend=c.current_spend,
            previous_spend=c.previous_spend,
            change_amount=c.change_amount,
            change_percentage=c.change_percentage,
            spend_percentage=c.spend_percentage,
            is_essential=c.is_essential,
            trend=c.trend,
        )
        for c in res.categories
    ]
    merchants_resp = [
        MerchantSpendingItemResponse(
            merchant_name=m.merchant_name,
            merchant_id=m.merchant_id,
            total_amount=m.total_amount,
            transaction_count=m.transaction_count,
            percentage_of_total=m.percentage_of_total,
        )
        for m in res.top_merchants
    ]

    return ApiResponse(
        data=CategorySpendingResponse(
            period_start=res.period_start,
            period_end=res.period_end,
            currency=res.currency,
            total_gross_expense=res.total_gross_expense,
            total_refunds=res.total_refunds,
            total_net_expense=res.total_net_expense,
            essential_spend=res.essential_spend,
            discretionary_spend=res.discretionary_spend,
            essential_percentage=res.essential_percentage,
            discretionary_percentage=res.discretionary_percentage,
            categories=categories_resp,
            top_merchants=merchants_resp,
        )
    )


@router.get(
    "/trends",
    response_model=ApiResponse[List[MonthlyTrendItemResponse]],
    summary="Get monthly spending, essential vs variable split, and cash flow trends",
)
async def get_spending_trends(
    months: int = Query(6, ge=1, le=24, description="Number of past months to retrieve"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[MonthlyTrendItemResponse]]:
    """Retrieve monthly trend aggregates across the past N months."""
    trends = await analyzer.get_monthly_trends(db, user_id, months_count=months)
    data = [
        MonthlyTrendItemResponse(
            month_key=t.month_key,
            month_label=t.month_label,
            period_start=t.period_start,
            period_end=t.period_end,
            income_total=t.income_total,
            total_spend=t.total_spend,
            essential_spend=t.essential_spend,
            variable_spend=t.variable_spend,
            net_cash_flow=t.net_cash_flow,
        )
        for t in trends
    ]
    return ApiResponse(data=data)


@router.get(
    "/merchants",
    response_model=ApiResponse[List[MerchantSpendingItemResponse]],
    summary="Get top merchants by spending concentration",
)
async def get_top_merchants(
    period_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[MerchantSpendingItemResponse]]:
    """Retrieve top merchants ranked by total spend."""
    res = await analyzer.analyze_period_spending(
        db, user_id, period_start=period_start, period_end=period_end
    )
    data = [
        MerchantSpendingItemResponse(
            merchant_name=m.merchant_name,
            merchant_id=m.merchant_id,
            total_amount=m.total_amount,
            transaction_count=m.transaction_count,
            percentage_of_total=m.percentage_of_total,
        )
        for m in res.top_merchants
    ]
    return ApiResponse(data=data)

