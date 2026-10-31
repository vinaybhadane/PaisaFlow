"""Transaction correction history model for auditability and explainability."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.categorization_rule import CategorizationRule
    from backend.app.models.transaction import Transaction
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class TransactionCorrection(Base):
    """Audit log preserving historical transaction corrections made by users or learning rules."""

    __tablename__ = "transaction_corrections"

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
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # e.g., 'category_id', 'transaction_type', 'merchant_id'
    old_value: Mapped[Dict[str, Any]] = mapped_column(
        JsonType,
        nullable=False,
    )
    new_value: Mapped[Dict[str, Any]] = mapped_column(
        JsonType,
        nullable=False,
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categorization_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reverted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    transaction: Mapped["Transaction"] = relationship("Transaction")
    rule: Mapped[Optional["CategorizationRule"]] = relationship("CategorizationRule")

    __table_args__ = (
        Index("ix_transaction_corrections_user_created", "user_id", "created_at"),
        Index("ix_transaction_corrections_tx_field", "transaction_id", "field_name"),
    )

