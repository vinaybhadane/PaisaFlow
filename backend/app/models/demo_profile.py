"""Demo profile database model for synthetic personas."""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.account import Account
    from backend.app.models.user import User


class DemoProfile(Base):
    """Synthetic persona representation (e.g. Asha Mehta, Kabir Shah)."""

    __tablename__ = "demo_profiles"

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
    persona_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="demo_profiles")
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="demo_profile")
