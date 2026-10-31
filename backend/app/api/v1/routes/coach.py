"""API route handlers for the AI Financial Coach."""

from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.db.dependencies import get_db
from backend.app.intelligence.coach.coach_service import CoachService
from backend.app.schemas.coach import (
    CoachConversationDetail,
    CoachConversationSummary,
    CoachMessageRequest,
    CoachMessageResponse,
    SuggestedPromptsResponse,
)
from backend.app.schemas.common import ApiResponse

router = APIRouter(prefix="/coach", tags=["AI Financial Coach"])
service = CoachService()


@router.post(
    "/messages",
    response_model=ApiResponse[CoachMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI Financial Coach",
)
async def send_message(
    payload: CoachMessageRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CoachMessageResponse]:
    """Send a financial question to the AI Coach and receive a grounded response."""
    try:
        result = await service.send_message(
            db=db,
            user_id=user_id,
            message=payload.message,
            conversation_id=payload.conversation_id,
        )
        return ApiResponse(data=CoachMessageResponse(**result))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/conversations",
    response_model=ApiResponse[List[CoachConversationSummary]],
    summary="List all coach conversations for current user",
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100, description="Max conversations to retrieve"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[CoachConversationSummary]]:
    """Retrieve user's coach conversations with summary metadata."""
    conversations = await service.list_conversations(db=db, user_id=user_id, limit=limit)
    return ApiResponse(data=[CoachConversationSummary(**c) for c in conversations])


@router.get(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[CoachConversationDetail],
    summary="Get conversation message history",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CoachConversationDetail]:
    """Retrieve complete message thread for a specific conversation."""
    conv = await service.get_conversation(
        db=db, user_id=user_id, conversation_id=conversation_id
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return ApiResponse(data=CoachConversationDetail(**conv))


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Delete a coach conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[Dict[str, Any]]:
    """Delete a conversation and all its messages."""
    success = await service.delete_conversation(
        db=db, user_id=user_id, conversation_id=conversation_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return ApiResponse(data={"deleted": True, "conversation_id": str(conversation_id)})


@router.get(
    "/prompts",
    response_model=ApiResponse[SuggestedPromptsResponse],
    summary="Get starter questions for AI Financial Coach",
)
async def get_starter_prompts() -> ApiResponse[SuggestedPromptsResponse]:
    """Return starter prompt suggestions for quick user exploration."""
    prompts = service.get_starter_prompts()
    return ApiResponse(data=SuggestedPromptsResponse(prompts=prompts))

