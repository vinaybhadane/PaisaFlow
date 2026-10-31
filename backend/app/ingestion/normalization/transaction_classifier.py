"""Transaction direction and type classification."""

import re
from typing import List, Optional, Tuple


class TransactionClassifier:
    """Classifies transaction direction (debit/credit) and type (expense/income/transfer/refund/fee)."""

    TRANSFER_KEYWORDS = [
        r"\b(?:TRF TO|TRF FROM|TRANSFER TO|TRANSFER FROM|INTERNAL TRANSFER|OWN ACCT|SELF TRANSFER)\b",
        r"\b(?:TO SAVINGS|FROM CHECKING|TO CHECKING|FROM SAVINGS)\b",
    ]

    REFUND_KEYWORDS = [
        r"\b(?:REFUND|REVERSAL|RTN|CASHBACK|RETURNED|CHARGE REVERSAL)\b",
    ]

    FEE_KEYWORDS = [
        r"\b(?:ANNUAL FEE|MAINTENANCE FEE|SERVICE CHARGE|PENALTY|OVERDRAFT|SMS CHARGE)\b",
    ]

    CREDIT_KEYWORDS = [
        r"\b(?:SALARY|PAYROLL|STIPEND|WAGES|DIRECT DEP|INTEREST CREDIT|DIVIDEND)\b",
    ]

    @classmethod
    def classify(
        cls,
        description: str,
        debit_amount_present: bool = False,
        credit_amount_present: bool = False,
        amount_is_negative: bool = False,
        direction_hint: Optional[str] = None,
        direction: Optional[str] = None,
        merchant_name: Optional[str] = None,
    ) -> Tuple[str, str, bool]:
        """Classify direction, transaction type, and whether transaction should be excluded from cash flow.

        Returns:
            (direction: 'debit' | 'credit', transaction_type: str, is_excluded: bool)
        """
        text = description.upper()

        # Determine direction
        if direction in ("debit", "credit"):
            resolved_dir = direction
        elif debit_amount_present and not credit_amount_present:
            resolved_dir = "debit"
        elif credit_amount_present and not debit_amount_present:
            resolved_dir = "credit"
        elif direction_hint in ("debit", "credit"):
            resolved_dir = direction_hint
        elif amount_is_negative:
            resolved_dir = "debit"
        else:
            # Check description keywords for credit vs debit
            if any(re.search(kw, text) for kw in cls.CREDIT_KEYWORDS + cls.REFUND_KEYWORDS):
                resolved_dir = "credit"
            else:
                resolved_dir = "debit"

        # Check for own-account transfers (excluded from spending/income calculations)
        for kw in cls.TRANSFER_KEYWORDS:
            if re.search(kw, text):
                return resolved_dir, "transfer", True

        # Check for refunds (always credits, never ordinary income)
        for kw in cls.REFUND_KEYWORDS:
            if re.search(kw, text):
                return "credit", "refund", False

        # If credit
        if resolved_dir == "credit":
            return "credit", "income", False

        # If debit
        for kw in cls.FEE_KEYWORDS:
            if re.search(kw, text):
                return "debit", "fee", False

        return "debit", "expense", False

    @classmethod
    def classify_for_audit(
        cls,
        direction: str,
        description: str,
        merchant_name: Optional[str] = None,
    ) -> Tuple[str, bool, List[str]]:
        """Convenience method returning (transaction_type, is_excluded, warnings)."""
        _, tx_type, is_excluded = cls.classify(
            description=description,
            direction=direction,
            merchant_name=merchant_name,
        )
        warnings: List[str] = []
        if is_excluded:
            warnings.append("Excluded own-account internal transfer.")
        return tx_type, is_excluded, warnings
