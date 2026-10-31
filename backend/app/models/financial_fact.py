"""Financial facts and profile snapshot database models (Living Money Model)."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class FinancialFact(Base, TimestampMixin):
    """Effective-dated financial facts supporting the Living Money Model."""

    __tablename__ = "financial_facts"

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
    fact_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # income, fixed_cost, savings_balance, emergency_target, other
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # user_confirmed, transaction_inferred, scenario_assumption, system_calculated
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_reference: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="financial_facts")

    __table_args__ = (
        Index("ix_financial_facts_user_type_from", "user_id", "fact_type", "effective_from"),
    )


class ProfileSnapshot(Base):
    """Immutable periodic snapshots of a user's financial profile."""

    __tablename__ = "profile_snapshots"

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
    snapshot_date: Mapped[Date] = mapped_column(Date, nullable=False)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    income_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    expense_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    net_cash_flow: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    fixed_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    variable_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    data_coverage: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    user: Mapped["User"] = relationship("User")
