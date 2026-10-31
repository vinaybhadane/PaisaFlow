"""Recurring commitments, observations, and price change database models."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.merchant import Merchant
    from backend.app.models.user import User

# Use JSON with JSONB variant for PostgreSQL
JsonType = JSON().with_variant(JSONB, "postgresql")


class RecurringCommitment(Base, TimestampMixin):
    """Detected and confirmed recurring obligations (subscriptions, utilities, rent)."""

    __tablename__ = "recurring_commitments"

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
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cadence: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # weekly, fortnightly, monthly, quarterly, half_yearly, yearly, custom
    estimated_cadence_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    typical_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    min_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=True,
    )
    max_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    confidence: Mapped[str] = mapped_column(
        String(32),
        default="medium",
        nullable=False,
    )  # high, medium, low
    status: Mapped[str] = mapped_column(
        String(32),
        default="likely",
        nullable=False,
    )  # likely, confirmed, rejected, review_required
    last_observed_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    next_expected_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recurring_commitments")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    observations: Mapped[List["RecurringObservation"]] = relationship(
        "RecurringObservation",
        back_populates="commitment",
        cascade="all, delete-orphan",
    )
    price_changes: Mapped[List["PriceChangeEvent"]] = relationship(
        "PriceChangeEvent",
        back_populates="commitment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_recurring_commitments_user_status", "user_id", "status"),)


class RecurringObservation(Base):
    """Historical transaction observations supporting a recurring pattern."""

    __tablename__ = "recurring_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observed_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    observed_date: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    commitment: Mapped["RecurringCommitment"] = relationship("RecurringCommitment", back_populates="observations")


class PriceChangeEvent(Base):
    """Price or billing amount changes detected for recurring commitments."""

    __tablename__ = "price_change_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    new_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    absolute_change: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    percentage_change: Mapped[Decimal] = mapped_column(
        Numeric(8, 2, asdecimal=True),
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="possible",
        nullable=False,
    )  # possible, confirmed_by_user, dismissed

    # Relationship
    commitment: Mapped["RecurringCommitment"] = relationship("RecurringCommitment", back_populates="price_changes")
