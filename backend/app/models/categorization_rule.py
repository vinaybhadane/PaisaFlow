"""Categorization rule database model for personalized classification."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.category import Category
    from backend.app.models.transaction import Transaction
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class CategorizationRule(Base):
    """User-scoped deterministic categorization rule learned from corrections or user preference."""

    __tablename__ = "categorization_rules"

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
    scope_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # exact_merchant, merchant_alias, description_contains, merchant_and_context
    scope_value: Mapped[Dict[str, Any]] = mapped_column(
        JsonType,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subcategory_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    source_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    user: Mapped["User"] = relationship("User")
    category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    source_transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")

    __table_args__ = (
        Index("ix_categorization_rules_user_priority", "user_id", "priority"),
        Index("ix_categorization_rules_user_active", "user_id", "is_active"),
    )

