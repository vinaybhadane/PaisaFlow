"""Recurring commitment database service and lifecycle management.

Handles candidate persistence, idempotent updating, review status transitions,
observation linking, and price change tracking using AsyncSession.
"""

from decimal import Decimal
import logging
import traceback
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.intelligence.recurring.detector import RecurringDetector
from backend.app.models.recurring_commitment import (
    PriceChangeEvent,
    RecurringCommitment,
    RecurringObservation,
)
from backend.app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class RecurringCommitmentService:
    """Service for managing recurring commitments and observations."""

    def __init__(self, detector: Optional[RecurringDetector] = None):
        self.detector = detector or RecurringDetector()

    async def run_detection_for_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[RecurringCommitment]:
        """Detect and persist recurring commitments from the user's transactions.

        Idempotent: updates existing commitments and adds new observations without
        overwriting user decisions (confirmed/rejected).
        """
        # Fetch user's eligible transactions
        tx_stmt = (
            select(Transaction)
            .options(selectinload(Transaction.merchant))
            .where(
                Transaction.user_id == user_id,
                Transaction.is_excluded.is_(False),
                Transaction.transaction_type.notin_(["transfer", "refund"]),
            )
            .order_by(Transaction.transaction_date.asc())
        )
        tx_res = await db.execute(tx_stmt)
        transactions = list(tx_res.scalars().all())

        if not transactions:
            return []

        # Run detector (deterministic arithmetic)
        detected_candidates = self.detector.detect_candidates_from_transactions(transactions)

        persisted_commitments: List[RecurringCommitment] = []

        for candidate in detected_candidates:
            # Check if commitment already exists
            if candidate.merchant_id is not None:
                existing_stmt = select(RecurringCommitment).where(
                    RecurringCommitment.user_id == user_id,
                    RecurringCommitment.merchant_id == candidate.merchant_id,
                )
            else:
                existing_stmt = select(RecurringCommitment).where(
                    RecurringCommitment.user_id == user_id,
                    RecurringCommitment.display_name == candidate.display_name,
                )

            existing_res = await db.execute(existing_stmt)
            existing = existing_res.scalar_one_or_none()

            if existing:
                commitment = existing
                # If user already explicitly reviewed (confirmed or rejected), preserve status!
                if commitment.status not in ("confirmed", "rejected"):
                    commitment.status = candidate.status

                commitment.cadence = candidate.cadence
                commitment.estimated_cadence_days = candidate.estimated_cadence_days
                commitment.typical_amount = candidate.typical_amount
                commitment.min_amount = candidate.min_amount
                commitment.max_amount = candidate.max_amount
                commitment.confidence = candidate.confidence
                commitment.last_observed_date = candidate.last_observed_date
                commitment.next_expected_date = candidate.next_expected_date
                commitment.evidence = candidate.evidence
            else:
                commitment = RecurringCommitment(
                    user_id=user_id,
                    merchant_id=candidate.merchant_id,
                    display_name=candidate.display_name,
                    cadence=candidate.cadence,
                    estimated_cadence_days=candidate.estimated_cadence_days,
                    typical_amount=candidate.typical_amount,
                    min_amount=candidate.min_amount,
                    max_amount=candidate.max_amount,
                    currency=candidate.currency,
                    confidence=candidate.confidence,
                    status=candidate.status,
                    last_observed_date=candidate.last_observed_date,
                    next_expected_date=candidate.next_expected_date,
                    evidence=candidate.evidence,
                )
                db.add(commitment)
                await db.flush()  # Ensure commitment has an ID

            # Link observations idempotently
            obs_stmt = select(RecurringObservation.transaction_id).where(
                RecurringObservation.commitment_id == commitment.id
            )
            obs_res = await db.execute(obs_stmt)
            existing_obs_tx_ids = set(obs_res.scalars().all())

            for obs_record in candidate.observations:
                if obs_record.transaction_id not in existing_obs_tx_ids:
                    new_obs = RecurringObservation(
                        commitment_id=commitment.id,
                        transaction_id=obs_record.transaction_id,
                        observed_amount=obs_record.observed_amount,
                        observed_date=obs_record.observed_date,
                    )
                    db.add(new_obs)

            # Persist price change events idempotently
            for pc in candidate.price_changes:
                pc_stmt = select(PriceChangeEvent.id).where(
                    PriceChangeEvent.commitment_id == commitment.id,
                    PriceChangeEvent.previous_amount == pc.previous_amount,
                    PriceChangeEvent.new_amount == pc.new_amount,
                )
                pc_res = await db.execute(pc_stmt)
                pc_exists = pc_res.scalar_one_or_none()

                if not pc_exists:
                    new_pc = PriceChangeEvent(
                        commitment_id=commitment.id,
                        previous_amount=pc.previous_amount,
                        new_amount=pc.new_amount,
                        absolute_change=pc.absolute_change,
                        percentage_change=pc.percentage_change,
                        status=pc.status,
                        evidence=pc.evidence,
                    )
                    db.add(new_pc)

            persisted_commitments.append(commitment)

        # Run Gemini AI subscription intelligence to detect subscriptions from descriptions
        # and automatically track next billing dates predicted from price and debited date
        try:
            from backend.app.intelligence.recurring.gemini_subscription_service import GeminiSubscriptionService
            sub_service = GeminiSubscriptionService()
            gemini_commitments = await sub_service.process_and_persist_subscriptions(db, user_id, transactions)
            existing_ids = {c.id for c in persisted_commitments}
            for gc in gemini_commitments:
                if gc.id not in existing_ids:
                    persisted_commitments.append(gc)
                    existing_ids.add(gc.id)
        except Exception as e:
            logger.error(f"Error running Gemini subscription detection: {e}\n{traceback.format_exc()}")

        await db.commit()
        return persisted_commitments

    async def get_user_commitments(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        cadence: Optional[str] = None,
    ) -> List[RecurringCommitment]:
        """Fetch recurring commitments for a user with optional filtering."""
        stmt = (
            select(RecurringCommitment)
            .options(selectinload(RecurringCommitment.merchant))
            .where(RecurringCommitment.user_id == user_id)
            .order_by(RecurringCommitment.typical_amount.desc())
        )

        if status:
            stmt = stmt.where(RecurringCommitment.status == status)
        if cadence:
            stmt = stmt.where(RecurringCommitment.cadence == cadence)

        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_commitment_by_id(
        self, db: AsyncSession, user_id: uuid.UUID, commitment_id: uuid.UUID
    ) -> RecurringCommitment:
        """Fetch a specific commitment ensuring user ownership."""
        stmt = (
            select(RecurringCommitment)
            .options(
                selectinload(RecurringCommitment.observations),
                selectinload(RecurringCommitment.price_changes),
                selectinload(RecurringCommitment.merchant),
            )
            .where(
                RecurringCommitment.id == commitment_id,
                RecurringCommitment.user_id == user_id,
            )
        )
        res = await db.execute(stmt)
        commitment = res.scalar_one_or_none()
        if not commitment:
            raise NotFoundError(f"Recurring commitment {commitment_id} not found.")
        return commitment

    async def review_commitment(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        commitment_id: uuid.UUID,
        action: str,
    ) -> RecurringCommitment:
        """Process user review action on a recurring commitment.

        Actions: 'confirm', 'reject', 'review_required'.
        """
        commitment = await self.get_commitment_by_id(db, user_id, commitment_id)

        allowed_actions = {
            "confirm": "confirmed",
            "reject": "rejected",
            "review_required": "review_required",
        }

        if action not in allowed_actions:
            raise ValidationError(
                f"Invalid review action '{action}'. Must be one of: {list(allowed_actions.keys())}"
            )

        new_status = allowed_actions[action]
        commitment.status = new_status
        await db.commit()
        await db.refresh(commitment)
        return commitment

    async def update_commitment(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        commitment_id: uuid.UUID,
        display_name: Optional[str] = None,
        cadence: Optional[str] = None,
        typical_amount: Optional[Decimal] = None,
        status: Optional[str] = None,
    ) -> RecurringCommitment:
        """Update editable fields of a recurring commitment."""
        commitment = await self.get_commitment_by_id(db, user_id, commitment_id)

        if display_name is not None:
            clean_name = display_name.strip()
            if not clean_name:
                raise ValidationError("Display name cannot be empty.")
            commitment.display_name = clean_name

        if cadence is not None:
            valid_cadences = {
                "weekly",
                "fortnightly",
                "monthly",
                "quarterly",
                "half_yearly",
                "yearly",
                "custom",
            }
            if cadence not in valid_cadences:
                raise ValidationError(
                    f"Invalid cadence '{cadence}'. Allowed: {sorted(list(valid_cadences))}"
                )
            commitment.cadence = cadence

        if typical_amount is not None:
            if typical_amount <= Decimal("0.00"):
                raise ValidationError("Typical amount must be greater than zero.")
            commitment.typical_amount = typical_amount

        if status is not None:
            valid_statuses = {"likely", "confirmed", "rejected", "review_required"}
            if status not in valid_statuses:
                raise ValidationError(
                    f"Invalid status '{status}'. Allowed: {sorted(list(valid_statuses))}"
                )
            commitment.status = status

        await db.commit()
        await db.refresh(commitment)
        return commitment

    async def get_price_changes_for_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[PriceChangeEvent]:
        """Fetch all price change events across a user's recurring commitments."""
        stmt = (
            select(PriceChangeEvent)
            .join(RecurringCommitment)
            .where(RecurringCommitment.user_id == user_id)
            .order_by(PriceChangeEvent.detected_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
