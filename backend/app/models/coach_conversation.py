"""Coach conversation and message database models."""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class CoachConversation(Base):
    """A user's conversation session with the AI Financial Coach."""

    __tablename__ = "coach_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="Financial Consultation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="coach_conversations")
    messages: Mapped[List["CoachMessage"]] = relationship(
        "CoachMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CoachMessage.created_at",
    )


class CoachMessage(Base):
    """An individual message in a coach conversation."""

    __tablename__ = "coach_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' or 'coach'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    grounded_facts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JsonType, nullable=True)
    assumptions: Mapped[Optional[List[str]]] = mapped_column(JsonType, nullable=True)
    warnings: Mapped[Optional[List[str]]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    conversation: Mapped["CoachConversation"] = relationship(
        "CoachConversation",
        back_populates="messages",
    )

