"""Deterministic transaction duplicate fingerprinting."""

from datetime import date
from decimal import Decimal
import hashlib
from typing import Optional
import uuid


class DuplicateFingerprintGenerator:
    """Generates explainable, deterministic duplicate fingerprints for transactions."""

    @classmethod
    def generate_fingerprint(
        cls,
        user_id: uuid.UUID,
        account_id: Optional[uuid.UUID],
        transaction_date: date,
        amount: Decimal,
        direction: str = "debit",
        normalized_description: str = "",
        reference_str: Optional[str] = None,
    ) -> str:
        """Generate a SHA-256 fingerprint hash for duplicate detection."""
        acct_part = str(account_id) if account_id else str(user_id)
        ref_part = f":{reference_str.strip().upper()}" if reference_str and reference_str.strip() else ""

        raw = (
            f"{acct_part}:"
            f"{transaction_date.isoformat()}:"
            f"{str(amount.quantize(Decimal('0.01')))}:"
            f"{direction.lower()}:"
            f"{normalized_description.strip().upper()}"
            f"{ref_part}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def generate(
        cls,
        user_id: uuid.UUID,
        account_id: Optional[uuid.UUID],
        transaction_date: date,
        amount: Decimal,
        normalized_description: str = "",
        direction: str = "debit",
        reference_str: Optional[str] = None,
    ) -> str:
        """Convenience alias for generate_fingerprint."""
        return cls.generate_fingerprint(
            user_id=user_id,
            account_id=account_id,
            transaction_date=transaction_date,
            amount=amount,
            direction=direction,
            normalized_description=normalized_description,
            reference_str=reference_str,
        )
