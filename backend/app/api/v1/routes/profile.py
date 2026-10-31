"""API route handlers for Living Money Model, financial facts, summaries, and snapshots."""

from datetime import date
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.living_model.engine import LivingMoneyModelEngine
from backend.app.intelligence.living_model.fact_resolver import FinancialFactResolver
from backend.app.intelligence.living_model.profile_builder import ProfileBuilder
from backend.app.intelligence.living_model.snapshots import SnapshotManager
from backend.app.models.demo_profile import DemoProfile
from backend.app.models.user import User
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.living_model import (
    DataCoverageResponse,
    DemoPersonaResponse,
    FinancialFactCreateRequest,
    FinancialFactResponse,
    FinancialFactUpdateRequest,
    FinancialSummaryResponse,
    LivingProfileResponse,
    ProfileSnapshotResponse,
    SnapshotRecomputeRequest,
)

router = APIRouter(prefix="/profile", tags=["Living Money Model"])
summary_router = APIRouter(prefix="/financial-summary", tags=["Financial Summary"])

engine = LivingMoneyModelEngine()
fact_resolver = FinancialFactResolver()
profile_builder = ProfileBuilder(fact_resolver)
snapshot_manager = SnapshotManager(profile_builder)


# ============================================================================
# Financial Summary Routes (/api/v1/financial-summary)
# ============================================================================

@summary_router.get(
    "",
    response_model=ApiResponse[FinancialSummaryResponse],
    summary="Compute deterministic financial summary for a date window",
)
async def get_financial_summary(
    period_start: Optional[date] = Query(None, description="Start date of period (YYYY-MM-DD)"),
    period_end: Optional[date] = Query(None, description="End date of period (YYYY-MM-DD)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FinancialSummaryResponse]:
    """Compute period income, gross/net expenses, refunds, excluded transfers, and savings rate.

    Deterministic implementation of docs/10_FINANCIAL_LOGIC.md.
    """
    summary = await profile_builder.build_summary(
        db, user_id, period_start=period_start, period_end=period_end
    )

    coverage_resp = DataCoverageResponse(
        days_covered=summary.coverage.days_covered,
        transaction_count=summary.coverage.transaction_count,
        account_count=summary.coverage.account_count,
        earliest_date=summary.coverage.earliest_date,
        latest_date=summary.coverage.latest_date,
        is_complete_month=summary.coverage.is_complete_month,
        coverage_status=summary.coverage.coverage_status,
        missing_periods_notes=summary.coverage.missing_periods_notes,
    )

    data = FinancialSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        currency=summary.currency,
        income_total=summary.income_total,
        expense_gross=summary.expense_gross,
        refunds_total=summary.refunds_total,
        expense_net=summary.expense_net,
        transfers_excluded_total=summary.transfers_excluded_total,
        transfers_excluded_count=summary.transfers_excluded_count,
        net_cash_flow=summary.net_cash_flow,
        cash_flow_savings_rate=summary.cash_flow_savings_rate,
        essential_expense_total=summary.essential_expense_total,
        variable_expense_total=summary.variable_expense_total,
        recurring_commitments_monthly=summary.recurring_commitments_monthly,
        available_money_estimate=summary.available_money_estimate,
        coverage=coverage_resp,
        notes=summary.notes,
    )
    return ApiResponse(data=data)


# ============================================================================
# Profile Routes (/api/v1/profile)
# ============================================================================

@router.get(
    "",
    response_model=ApiResponse[LivingProfileResponse],
    summary="Get current Living Money Model profile with active facts and provenance",
)
async def get_profile(
    as_of_date: Optional[date] = Query(None, description="Target date for active profile (YYYY-MM-DD)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LivingProfileResponse]:
    """Compile user's active Living Money Model profile."""
    profile_data = await engine.get_living_profile(db, user_id, as_of_date=as_of_date)
    return ApiResponse(data=LivingProfileResponse(**profile_data))


@router.get(
    "/personas",
    response_model=ApiResponse[List[DemoPersonaResponse]],
    summary="List available synthetic demo personas for interactive exploration",
)
async def list_demo_personas(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[DemoPersonaResponse]]:
    """Retrieve all seeded synthetic personas (e.g. Asha Mehta, Kabir Shah) for demo switching."""
    stmt = (
        select(DemoProfile, User)
        .join(User, DemoProfile.user_id == User.id)
        .order_by(DemoProfile.created_at.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    personas = [
        DemoPersonaResponse(
            user_id=p.user_id,
            display_name=u.display_name,
            email=u.email,
            persona_key=p.persona_key,
            profile_label=p.profile_label,
            is_synthetic=p.is_synthetic,
        )
        for p, u in rows
    ]
    return ApiResponse(data=personas)


@router.get(
    "/history",
    response_model=ApiResponse[List[ProfileSnapshotResponse]],
    summary="Get historical periodic profile snapshots",
)
async def get_profile_history(
    limit: int = Query(12, ge=1, le=60, description="Max snapshots to retrieve"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[ProfileSnapshotResponse]]:
    """Retrieve immutable periodic snapshots of user financial health."""
    snapshots = await snapshot_manager.get_user_snapshots(db, user_id, limit=limit)
    return ApiResponse(
        data=[ProfileSnapshotResponse.model_validate(s) for s in snapshots]
    )


@router.post(
    "/facts",
    response_model=ApiResponse[FinancialFactResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create or confirm an effective-dated financial fact",
)
async def create_fact(
    payload: FinancialFactCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FinancialFactResponse]:
    """Create a user-confirmed or inferred financial fact.

    User-confirmed facts strictly take precedence over inferred patterns.
    """
    fact = await fact_resolver.create_fact(
        db=db,
        user_id=user_id,
        fact_type=payload.fact_type,
        label=payload.label,
        amount=payload.amount,
        currency=payload.currency,
        source_type=payload.source_type,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        confidence=payload.confidence,
        source_reference=payload.source_reference,
    )
    return ApiResponse(data=FinancialFactResponse.model_validate(fact))


@router.patch(
    "/facts/{fact_id}",
    response_model=ApiResponse[FinancialFactResponse],
    summary="Update an existing financial fact preserving historical provenance",
)
async def update_fact(
    fact_id: uuid.UUID,
    payload: FinancialFactUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FinancialFactResponse]:
    """Update editable attributes of a financial fact."""
    fact = await fact_resolver.update_fact(
        db=db,
        user_id=user_id,
        fact_id=fact_id,
        label=payload.label,
        amount=payload.amount,
        effective_to=payload.effective_to,
        confidence=payload.confidence,
    )
    return ApiResponse(data=FinancialFactResponse.model_validate(fact))


@router.post(
    "/snapshots/recompute",
    response_model=ApiResponse[ProfileSnapshotResponse],
    summary="Idempotently recompute and persist a profile snapshot for a period",
)
async def recompute_snapshot(
    payload: SnapshotRecomputeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProfileSnapshotResponse]:
    """Recompute immutable profile snapshot for the given period."""
    snapshot = await snapshot_manager.create_or_update_snapshot(
        db=db,
        user_id=user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return ApiResponse(data=ProfileSnapshotResponse.model_validate(snapshot))
