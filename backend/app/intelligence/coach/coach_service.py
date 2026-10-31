"""AI Financial Coach Orchestrator Service.

Coordinates context extraction, LLM communication, conversation persistence,
and user-isolated history management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.intelligence.coach.context_builder import FinancialContextBuilder
from backend.app.intelligence.coach.gemini_service import GeminiCoachService
from backend.app.intelligence.coach.prompts import STARTER_PROMPTS
from backend.app.models.coach_conversation import CoachConversation, CoachMessage


class CoachService:
    """Orchestration service for PaisaFlow AI Financial Coach."""

    def __init__(
        self,
        context_builder: Optional[FinancialContextBuilder] = None,
        gemini_service: Optional[GeminiCoachService] = None,
    ):
        self.context_builder = context_builder or FinancialContextBuilder()
        self.gemini_service = gemini_service or GeminiCoachService()

    async def send_message(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        message: str,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Send a message to the AI Financial Coach and persist both prompt and response."""
        user_message_clean = message.strip()
        if not user_message_clean:
            raise ValueError("Message cannot be empty.")

        # 1. Resolve or create conversation
        conversation: Optional[CoachConversation] = None
        if conversation_id:
            res = await db.execute(
                select(CoachConversation).where(
                    CoachConversation.id == conversation_id,
                    CoachConversation.user_id == user_id,
                )
            )
            conversation = res.scalar_one_or_none()
            if not conversation:
                raise ValueError("Conversation not found or access denied.")
        else:
            # Create new conversation with title from message preview
            title = user_message_clean[:60] + ("..." if len(user_message_clean) > 60 else "")
            conversation = CoachConversation(
                user_id=user_id,
                title=title,
            )
            db.add(conversation)
            await db.flush()

        # 2. Persist User Message
        user_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="user",
            content=user_message_clean,
            grounded_facts=None,
            assumptions=None,
            warnings=None,
        )
        db.add(user_msg)
        await db.flush()

        # 3. Build strictly bounded, deterministic financial context
        context_data = await self.context_builder.build_context(db, user_id)

        # 4. Fetch recent conversation history for coherence (last 6 messages)
        hist_stmt = (
            select(CoachMessage)
            .where(CoachMessage.conversation_id == conversation.id)
            .order_by(desc(CoachMessage.created_at))
            .limit(6)
        )
        hist_res = await db.execute(hist_stmt)
        recent_messages = list(reversed(hist_res.scalars().all()))

        history_items = [
            {"role": m.sender, "content": m.content}
            for m in recent_messages
            if m.id != user_msg.id
        ]

        # 5. Generate coach response via Gemini (or deterministic fallback)
        coach_res = await self.gemini_service.generate_response(
            user_message=user_message_clean,
            context_data=context_data,
            conversation_history=history_items,
        )

        # 6. Persist Coach Response
        coach_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="coach",
            content=coach_res["content"],
            grounded_facts=coach_res.get("grounded_facts"),
            assumptions=coach_res.get("assumptions"),
            warnings=coach_res.get("warnings"),
        )
        db.add(coach_msg)

        # Update conversation updated_at
        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(coach_msg)

        return {
            "id": coach_msg.id,
            "conversation_id": conversation.id,
            "sender": coach_msg.sender,
            "content": coach_msg.content,
            "grounded_facts": coach_msg.grounded_facts,
            "assumptions": coach_msg.assumptions,
            "warnings": coach_msg.warnings,
            "created_at": coach_msg.created_at,
            "is_live_gemini": coach_res.get("is_live_gemini", False),
        }

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List user's coach conversations with message counts."""
        # Query conversations with count of messages
        stmt = (
            select(
                CoachConversation,
                func.count(CoachMessage.id).label("message_count"),
            )
            .outerjoin(CoachMessage, CoachConversation.id == CoachMessage.conversation_id)
            .where(CoachConversation.user_id == user_id)
            .group_by(CoachConversation.id)
            .order_by(desc(CoachConversation.updated_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()

        return [
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "title": conv.title,
                "message_count": count,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
            }
            for conv, count in rows
        ]

    async def get_conversation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve conversation details and ordered message history."""
        stmt = (
            select(CoachConversation)
            .options(selectinload(CoachConversation.messages))
            .where(
                CoachConversation.id == conversation_id,
                CoachConversation.user_id == user_id,
            )
        )
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            return None

        return {
            "id": conv.id,
            "user_id": conv.user_id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "sender": m.sender,
                    "content": m.content,
                    "grounded_facts": m.grounded_facts,
                    "assumptions": m.assumptions,
                    "warnings": m.warnings,
                    "created_at": m.created_at,
                }
                for m in conv.messages
            ],
        }

    async def delete_conversation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Delete conversation and all messages with user ownership enforcement."""
        # Check ownership and fetch with messages
        res = await db.execute(
            select(CoachConversation)
            .options(selectinload(CoachConversation.messages))
            .where(
                CoachConversation.id == conversation_id,
                CoachConversation.user_id == user_id,
            )
        )
        conv = res.scalar_one_or_none()
        if not conv:
            return False

        await db.delete(conv)
        await db.commit()
        return True

    def get_starter_prompts(self) -> List[str]:
        """Return curated starter prompts for users."""
        return STARTER_PROMPTS
