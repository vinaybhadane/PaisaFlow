"""Import batch database model."""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.account import Account
    from backend.app.models.transaction import Transaction
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class ImportBatch(Base):
    """Lifecycle tracking for financial statement ingestion batches."""

    __tablename__ = "import_batches"

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
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # csv, pdf_text, pdf_ocr, sms_text, demo_seed
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="uploaded",
        nullable=False,
    )  # uploaded, processing, preview_ready, confirmed, completed, failed
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    account: Mapped[Optional["Account"]] = relationship("Account")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        primaryjoin="ImportBatch.id == foreign(Transaction.import_batch_id)",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_import_batches_user_created", "user_id", "created_at"),
    )

