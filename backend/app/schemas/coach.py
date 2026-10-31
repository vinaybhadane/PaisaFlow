"""Pydantic schemas for the AI Financial Coach API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CoachMessageRequest(BaseModel):
    """Payload to send a message to the AI Financial Coach."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User query or financial question",
    )
    conversation_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional existing conversation UUID to continue a thread",
    )


class CoachMessageResponse(BaseModel):
    """Structured response message from AI Coach or user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: str
    content: str
    grounded_facts: Optional[List[Dict[str, Any]]] = None
    assumptions: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime
    is_live_gemini: Optional[bool] = None


class CoachConversationSummary(BaseModel):
    """Summary item for a user's coach conversations list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class CoachConversationDetail(BaseModel):
    """Detailed conversation with ordered message history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[CoachMessageResponse] = Field(default_factory=list)


class SuggestedPromptsResponse(BaseModel):
    """List of curated starter prompts for the coach."""

    prompts: List[str]

