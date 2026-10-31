"""Account database model."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.demo_profile import DemoProfile
    from backend.app.models.transaction import Transaction
    from backend.app.models.user import User


class Account(Base, TimestampMixin):
    """Financial account entity (checking, savings, credit card, cash)."""

    __tablename__ = "accounts"

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
    demo_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("demo_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # checking, savings, credit_card, cash, other
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    demo_profile: Mapped[Optional["DemoProfile"]] = relationship("DemoProfile", back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
    )
