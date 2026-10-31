"""Amount statistical analysis and monthly planning equivalents for recurring commitments.

Follows docs/10_FINANCIAL_LOGIC.md strictly:
- Python Decimal for all money calculations
- Monthly equivalents:
  - monthly: amount
  - weekly: amount * 52 / 12
  - fortnightly: amount * 26 / 12
  - quarterly: amount / 3
  - half_yearly: amount / 6
  - yearly: amount / 12
- Stability classification: stable (< 5% spread) vs variable (>= 5% spread)
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional


TWOPLACES = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    """Round a Decimal amount to 2 decimal places using standard financial rounding."""
    return amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class AmountAnalysisResult:
    """Statistical summary of recurring payment amounts."""

    typical_amount: Decimal  # Median amount
    min_amount: Decimal
    max_amount: Decimal
    mean_amount: Decimal
    stability: str  # "stable" or "variable"
    monthly_equivalent: Decimal
    estimated_annual_cost: Decimal
    spread_percentage: Decimal


def calculate_monthly_equivalent(
    amount: Decimal, cadence: str, estimated_cadence_days: Optional[int] = None
) -> Decimal:
    """Calculate the monthly planning equivalent for a given cadence.

    Authoritative arithmetic from docs/10_FINANCIAL_LOGIC.md:
    - monthly: amount
    - weekly: amount * 52 / 12
    - fortnightly: amount * 26 / 12
    - quarterly: amount / 3
    - half_yearly: amount / 6
    - yearly: amount / 12

    These are planning equivalents, not actual charges.
    """
    if amount <= Decimal("0"):
        return Decimal("0.00")

    cadence_lower = cadence.lower().strip()

    if cadence_lower == "monthly":
        return round_money(amount)
    elif cadence_lower == "weekly":
        return round_money((amount * Decimal(52)) / Decimal(12))
    elif cadence_lower == "fortnightly":
        return round_money((amount * Decimal(26)) / Decimal(12))
    elif cadence_lower == "quarterly":
        return round_money(amount / Decimal(3))
    elif cadence_lower == "half_yearly":
        return round_money(amount / Decimal(6))
    elif cadence_lower == "yearly":
        return round_money(amount / Decimal(12))
    elif cadence_lower in ("custom", "irregular"):
        if estimated_cadence_days and estimated_cadence_days > 0:
            # (amount * 365) / (12 * estimated_cadence_days)
            annual = (amount * Decimal(365)) / Decimal(estimated_cadence_days)
            return round_money(annual / Decimal(12))
        return round_money(amount)
    else:
        return round_money(amount)


def analyze_amounts(
    amounts: List[Decimal], cadence: str, estimated_cadence_days: Optional[int] = None
) -> AmountAnalysisResult:
    """Analyze amount statistics for a recurring commitment.

    Args:
        amounts: List of observed payment amounts (Decimal).
        cadence: Detected cadence string.
        estimated_cadence_days: Optional cadence days for custom cadences.

    Returns:
        AmountAnalysisResult with median, min, max, stability, and monthly equivalent.
    """
    if not amounts:
        zero = Decimal("0.00")
        return AmountAnalysisResult(
            typical_amount=zero,
            min_amount=zero,
            max_amount=zero,
            mean_amount=zero,
            stability="stable",
            monthly_equivalent=zero,
            estimated_annual_cost=zero,
            spread_percentage=zero,
        )

    # Sort amounts
    sorted_amounts = sorted(amounts)
    n = len(sorted_amounts)

    # Median (typical amount)
    if n % 2 == 1:
        med = sorted_amounts[n // 2]
    else:
        med = (sorted_amounts[n // 2 - 1] + sorted_amounts[n // 2]) / Decimal(2)

    typical_amt = round_money(med)
    min_amt = round_money(sorted_amounts[0])
    max_amt = round_money(sorted_amounts[-1])
    mean_amt = round_money(sum(sorted_amounts) / Decimal(n))

    # Spread calculation
    if typical_amt > Decimal("0"):
        spread_pct = round_money(((max_amt - min_amt) / typical_amt) * Decimal(100))
    else:
        spread_pct = Decimal("0.00")

    # Stability: < 5% spread is considered stable fixed subscription/bill
    stability = "stable" if spread_pct < Decimal("5.00") else "variable"

    monthly_eq = calculate_monthly_equivalent(typical_amt, cadence, estimated_cadence_days)
    annual_cost = round_money(monthly_eq * Decimal(12))

    return AmountAnalysisResult(
        typical_amount=typical_amt,
        min_amount=min_amt,
        max_amount=max_amt,
        mean_amount=mean_amt,
        stability=stability,
        monthly_equivalent=monthly_eq,
        estimated_annual_cost=annual_cost,
        spread_percentage=spread_pct,
    )

