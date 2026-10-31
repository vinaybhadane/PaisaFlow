"""API route handlers for recurring commitment detection, review, and price changes."""

from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.recurring.amount_analysis import (
    calculate_monthly_equivalent,
    round_money,
)
from backend.app.intelligence.recurring.commitment_service import RecurringCommitmentService
from backend.app.models.recurring_commitment import RecurringCommitment
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.recurring import (
    CommitmentReviewRequest,
    CommitmentUpdateRequest,
    PriceChangeEventResponse,
    RecurringCommitmentDetailResponse,
    RecurringCommitmentResponse,
)

router = APIRouter(prefix="/recurring", tags=["Recurring"])
service = RecurringCommitmentService()


def enrich_commitment_response(commitment: RecurringCommitment) -> RecurringCommitmentResponse:
    """Enrich recurring commitment model with monthly planning equivalent and annual cost."""
    monthly_eq = calculate_monthly_equivalent(
        commitment.typical_amount,
        commitment.cadence,
        commitment.estimated_cadence_days,
    )
    annual_cost = round_money(monthly_eq * Decimal(12))

    return RecurringCommitmentResponse(
        id=commitment.id,
        user_id=commitment.user_id,
        merchant_id=commitment.merchant_id,
        display_name=commitment.display_name,
        cadence=commitment.cadence,
        estimated_cadence_days=commitment.estimated_cadence_days,
        typical_amount=commitment.typical_amount,
        min_amount=commitment.min_amount,
        max_amount=commitment.max_amount,
        currency=commitment.currency,
        confidence=commitment.confidence,
        status=commitment.status,
        last_observed_date=commitment.last_observed_date,
        next_expected_date=commitment.next_expected_date,
        evidence=commitment.evidence,
        monthly_equivalent=monthly_eq,
        estimated_annual_cost=annual_cost,
        created_at=commitment.created_at,
        updated_at=commitment.updated_at,
    )


@router.get(
    "",
    response_model=ApiResponse[List[RecurringCommitmentResponse]],
    summary="List recurring commitments with optional status or cadence filters",
)
async def list_commitments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    cadence: Optional[str] = Query(None, description="Filter by cadence"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[RecurringCommitmentResponse]]:
    """List detected and user-managed recurring obligations."""
    commitments = await service.get_user_commitments(
        db, user_id, status=status_filter, cadence=cadence
    )
    data = [enrich_commitment_response(c) for c in commitments]
    return ApiResponse(data=data)


@router.post(
    "/detect",
    response_model=ApiResponse[List[RecurringCommitmentResponse]],
    summary="Trigger on-demand recurring pattern detection across transactions",
)
async def detect_commitments(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[RecurringCommitmentResponse]]:
    """Analyze transaction history to detect recurring payments, subscriptions, and income."""
    commitments = await service.run_detection_for_user(db, user_id)
    data = [enrich_commitment_response(c) for c in commitments]
    return ApiResponse(data=data)


@router.get(
    "/price-changes",
    response_model=ApiResponse[List[PriceChangeEventResponse]],
    summary="List detected price change events across recurring commitments",
)
async def list_price_changes(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[PriceChangeEventResponse]]:
    """List historical price increases, decreases, and billing amount shifts."""
    events = await service.get_price_changes_for_user(db, user_id)
    return ApiResponse(data=[PriceChangeEventResponse.model_validate(e) for e in events])


@router.get(
    "/{commitment_id}",
    response_model=ApiResponse[RecurringCommitmentDetailResponse],
    summary="Get single recurring commitment detail with observations and price changes",
)
async def get_commitment(
    commitment_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecurringCommitmentDetailResponse]:
    """Retrieve full detail for a recurring commitment including observations."""
    c = await service.get_commitment_by_id(db, user_id, commitment_id)
    enriched = enrich_commitment_response(c)
    data = RecurringCommitmentDetailResponse(
        **enriched.model_dump(),
        observations=c.observations,
        price_changes=c.price_changes,
    )
    return ApiResponse(data=data)


@router.post(
    "/{commitment_id}/review",
    response_model=ApiResponse[RecurringCommitmentResponse],
    summary="Submit user review action (confirm, reject, review_required)",
)
async def review_commitment(
    commitment_id: uuid.UUID,
    payload: CommitmentReviewRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecurringCommitmentResponse]:
    """Confirm, reject, or request review for a detected recurring commitment."""
    c = await service.review_commitment(db, user_id, commitment_id, payload.action)
    return ApiResponse(data=enrich_commitment_response(c))


@router.patch(
    "/{commitment_id}",
    response_model=ApiResponse[RecurringCommitmentResponse],
    summary="Update editable fields of a recurring commitment",
)
async def update_commitment(
    commitment_id: uuid.UUID,
    payload: CommitmentUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecurringCommitmentResponse]:
    """Edit display name, typical amount, cadence, or status."""
    c = await service.update_commitment(
        db,
        user_id,
        commitment_id,
        display_name=payload.display_name,
        cadence=payload.cadence,
        typical_amount=payload.typical_amount,
        status=payload.status,
    )
    return ApiResponse(data=enrich_commitment_response(c))


@router.get(
    "/{commitment_id}/history",
    response_model=ApiResponse[RecurringCommitmentDetailResponse],
    summary="Get commitment history with supporting transactions and price change events",
)
async def get_commitment_history(
    commitment_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecurringCommitmentDetailResponse]:
    """Retrieve historical transaction observations and price change events."""
    c = await service.get_commitment_by_id(db, user_id, commitment_id)
    enriched = enrich_commitment_response(c)
    data = RecurringCommitmentDetailResponse(
        **enriched.model_dump(),
        observations=c.observations,
        price_changes=c.price_changes,
    )
    return ApiResponse(data=data)
