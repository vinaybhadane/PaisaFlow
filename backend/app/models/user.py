"""User database model."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.account import Account
    from backend.app.models.coach_conversation import CoachConversation
    from backend.app.models.demo_profile import DemoProfile
    from backend.app.models.financial_fact import FinancialFact
    from backend.app.models.goal import Goal
    from backend.app.models.recurring_commitment import RecurringCommitment
    from backend.app.models.scenario import Scenario
    from backend.app.models.transaction import Transaction


class User(Base, TimestampMixin):
    """User account entity. Every user-scoped resource enforces ownership through user_id."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    locale: Mapped[str] = mapped_column(String(32), default="en-IN", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Relationships
    demo_profiles: Mapped[List["DemoProfile"]] = relationship(
        "DemoProfile",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[List["Account"]] = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recurring_commitments: Mapped[List["RecurringCommitment"]] = relationship(
        "RecurringCommitment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    financial_facts: Mapped[List["FinancialFact"]] = relationship(
        "FinancialFact",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    goals: Mapped[List["Goal"]] = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    scenarios: Mapped[List["Scenario"]] = relationship(
        "Scenario",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    coach_conversations: Mapped[List["CoachConversation"]] = relationship(
        "CoachConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
