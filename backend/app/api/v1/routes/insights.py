"""API route handlers for explainable financial insights."""

from datetime import date
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.insights.insights_engine import InsightsEngine
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.insights import FinancialInsightResponse

router = APIRouter(prefix="/insights", tags=["Financial Insights"])
engine = InsightsEngine()


@router.get(
    "",
    response_model=ApiResponse[List[FinancialInsightResponse]],
    summary="Generate explainable, evidence-grounded financial insights",
)
async def get_insights(
    period_start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[FinancialInsightResponse]]:
    """Generate structured observations on spending concentration, spikes, savings rate, and recurring burden."""
    insights = await engine.generate_insights(
        db, user_id, period_start=period_start, period_end=period_end
    )
    data = [
        FinancialInsightResponse(
            insight_type=i.insight_type,
            title=i.title,
            explanation=i.explanation,
            metric_value=i.metric_value,
            change_percentage=i.change_percentage,
            period=i.period,
            confidence=i.confidence,
            severity=i.severity,
            evidence=i.evidence,
        )
        for i in insights
    ]
    return ApiResponse(data=data)

