"""API route handlers for user-specific categorization rules."""

from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.corrections.learning_rules import CategorizationRuleService
from backend.app.schemas.categorization_rule import (
    CategorizationRuleCreateRequest,
    CategorizationRuleResponse,
    CategorizationRuleUpdateRequest,
)
from backend.app.schemas.common import ApiResponse

router = APIRouter(prefix="/categorization-rules", tags=["Categorization Rules"])


@router.get(
    "",
    response_model=ApiResponse[List[CategorizationRuleResponse]],
    summary="List all categorization rules for the active user",
)
async def list_rules(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[CategorizationRuleResponse]]:
    """Retrieve user-scoped categorization rules ordered by priority."""
    rules = await CategorizationRuleService.list_user_rules(db, user_id=user_id)
    return ApiResponse(
        data=[CategorizationRuleResponse.model_validate(r) for r in rules]
    )


@router.post(
    "",
    response_model=ApiResponse[CategorizationRuleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user categorization rule",
)
async def create_rule(
    request: CategorizationRuleCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategorizationRuleResponse]:
    """Define an explicit user-specific categorization override rule."""
    rule = await CategorizationRuleService.create_rule(
        session=db,
        user_id=user_id,
        category_id=request.category_id,
        subcategory_id=request.subcategory_id,
        scope_type=request.scope_type,
        scope_value=request.scope_value,
        priority=request.priority,
        source_transaction_id=request.source_transaction_id,
    )
    return ApiResponse(data=CategorizationRuleResponse.model_validate(rule))


@router.patch(
    "/{rule_id}",
    response_model=ApiResponse[CategorizationRuleResponse],
    summary="Edit, enable or disable a categorization rule",
)
async def update_rule(
    rule_id: uuid.UUID,
    request: CategorizationRuleUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategorizationRuleResponse]:
    """Modify parameters of an existing user rule."""
    rule = await CategorizationRuleService.update_rule(
        session=db,
        user_id=user_id,
        rule_id=rule_id,
        is_active=request.is_active,
        priority=request.priority,
        category_id=request.category_id,
        subcategory_id=request.subcategory_id,
    )
    return ApiResponse(data=CategorizationRuleResponse.model_validate(rule))


@router.post(
    "/{rule_id}/undo",
    response_model=ApiResponse[CategorizationRuleResponse],
    summary="Deactivate or undo a categorization rule",
)
async def undo_rule(
    rule_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategorizationRuleResponse]:
    """Safely disable a rule while preserving the audit record."""
    rule = await CategorizationRuleService.deactivate_rule(
        session=db,
        user_id=user_id,
        rule_id=rule_id,
    )
    return ApiResponse(data=CategorizationRuleResponse.model_validate(rule))

