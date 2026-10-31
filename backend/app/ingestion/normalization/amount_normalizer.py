"""Monetary amount normalization using Python Decimal."""

from decimal import Decimal, InvalidOperation
import re
from typing import Optional, Tuple


class AmountNormalizer:
    """Normalizes financial text amounts into positive Decimal magnitudes with direction hint."""

    # Regex to clean symbols and currency text
    CURRENCY_CLEANER = re.compile(r"(?:INR|₹|Rs\.?|USD|\$|EUR|€|GBP|£)", re.IGNORECASE)

    @classmethod
    def parse_amount(
        cls,
        raw_val: Optional[str],
    ) -> Tuple[Optional[Decimal], bool, Optional[str]]:
        """Parse raw amount string into positive Decimal and negative flag.

        Returns:
            (magnitude: Decimal, is_negative: bool, error: Optional[str])
        """
        if raw_val is None:
            return None, False, "Amount value is None"

        text = str(raw_val).strip()
        if not text:
            return None, False, "Amount string is empty"

        # Check for accounting parentheses e.g. '(1,500.00)' -> negative
        is_negative = False
        if text.startswith("(") and text.endswith(")"):
            is_negative = True
            text = text[1:-1].strip()

        # Check for explicit signs
        if text.startswith("-"):
            is_negative = True
            text = text[1:].strip()
        elif text.startswith("+"):
            text = text[1:].strip()
        elif text.lower().endswith("dr"):
            is_negative = True
            text = text[:-2].strip()
        elif text.lower().endswith("cr"):
            is_negative = False
            text = text[:-2].strip()

        # Remove currency symbols and non-numeric artifacts except dots and commas
        text = cls.CURRENCY_CLEANER.sub("", text).strip()
        # Remove whitespace
        text = re.sub(r"\s+", "", text)

        # Standardize comma thousand separators: e.g. '12,500.00' -> '12500.00'
        # Check European style e.g. '12.500,00' if comma is last separator and dot is before
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                # European style: 1.250,50 -> 1250.50
                text = text.replace(".", "").replace(",", ".")
            else:
                # Standard Indian/US style: 12,500.00 -> 12500.00
                text = text.replace(",", "")
        elif "," in text and "." not in text:
            # Could be comma as decimal e.g. '1250,50' or thousand separator '12,500'
            parts = text.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                # 2 digits after comma -> decimal separator
                text = text.replace(",", ".")
            else:
                text = text.replace(",", "")

        try:
            magnitude = Decimal(text)
            if magnitude < 0:
                is_negative = True
                magnitude = abs(magnitude)

            # Quantize to 2 decimal places
            magnitude = magnitude.quantize(Decimal("0.01"))
            return magnitude, is_negative, None
        except (InvalidOperation, ValueError):
            return None, False, f"Cannot parse '{raw_val}' as a valid decimal monetary amount"

    @classmethod
    def normalize(
        cls,
        debit_val: Optional[str] = None,
        credit_val: Optional[str] = None,
        amount_val: Optional[str] = None,
    ) -> Tuple[Optional[Decimal], str, Optional[str]]:
        """Normalize amounts from debit/credit columns or a single signed amount column.

        Returns:
            (magnitude: Optional[Decimal], direction: 'debit' | 'credit', error: Optional[str])
        """
        if debit_val is not None and str(debit_val).strip():
            mag, _, err = cls.parse_amount(debit_val)
            return mag, "debit", err

        if credit_val is not None and str(credit_val).strip():
            mag, _, err = cls.parse_amount(credit_val)
            return mag, "credit", err

        if amount_val is not None and str(amount_val).strip():
            raw = str(amount_val).strip()
            mag, is_neg, err = cls.parse_amount(amount_val)
            # Explicit plus or 'cr' suffix implies credit
            is_credit = raw.startswith("+") or raw.lower().endswith("cr")
            direction = "credit" if is_credit else ("debit" if is_neg else "debit")
            return mag, direction, err

        return None, "debit", "No amount provided"
