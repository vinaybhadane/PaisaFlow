"""Goal database model."""

from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class Goal(Base, TimestampMixin):
    """User savings and financial target goals."""

    __tablename__ = "goals"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    current_saved_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        default=Decimal("0.00"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    target_date: Mapped[Date] = mapped_column(Date, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(16),
        default="medium",
        nullable=False,
    )  # low, medium, high
    contribution_frequency: Mapped[str] = mapped_column(
        String(16),
        default="monthly",
        nullable=False,
    )  # monthly, weekly
    planned_contribution: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )  # active, completed, paused, abandoned

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="goals")

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goals_target_amount_positive"),
        CheckConstraint("current_saved_amount >= 0", name="ck_goals_saved_amount_non_negative"),
        Index("ix_goals_user_status", "user_id", "status"),
    )
