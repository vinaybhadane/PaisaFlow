"""What-if scenario database model."""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.user import User

JsonType = JSON().with_variant(JSONB, "postgresql")


class Scenario(Base):
    """Saved what-if simulation records. Scenarios never mutate actual transaction records."""

    __tablename__ = "scenarios"

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
    scenario_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_parameters: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False)
    baseline_result: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False)
    scenario_result: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False)
    assumptions: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="scenarios")
