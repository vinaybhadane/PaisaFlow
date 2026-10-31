"""Merchant and merchant alias database models."""

from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Merchant(Base):
    """Canonical merchant identity."""

    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_fictional_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    aliases: Mapped[List["MerchantAlias"]] = relationship(
        "MerchantAlias",
        back_populates="merchant",
        cascade="all, delete-orphan",
    )


class MerchantAlias(Base):
    """Alias descriptor patterns mapping to canonical merchants."""

    __tablename__ = "merchant_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_pattern: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(
        String(32),
        default="exact",
        nullable=False,
    )  # exact, normalized, limited_regex, fuzzy_reference
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="aliases")

