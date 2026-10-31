"""Transaction database model."""

from decimal import Decimal
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
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
    from backend.app.models.account import Account
    from backend.app.models.category import Category
    from backend.app.models.merchant import Merchant
    from backend.app.models.user import User


class Transaction(Base, TimestampMixin):
    """Financial transaction entity. Stores positive magnitude plus separate direction/type."""

    __tablename__ = "transactions"

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
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    posted_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2, asdecimal=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # debit, credit
    transaction_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # expense, income, transfer, refund, fee, adjustment, unknown
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subcategory_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    categorization_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(32),
        default="confirmed",
        nullable=False,
    )  # pending, confirmed, corrected, flagged
    duplicate_fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant")
    category: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[category_id])

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transactions_amount_non_negative"),
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_cat_date", "user_id", "category_id", "transaction_date"),
        Index("ix_transactions_user_merch_date", "user_id", "merchant_id", "transaction_date"),
        Index("ix_transactions_user_fingerprint", "user_id", "duplicate_fingerprint"),
    )
