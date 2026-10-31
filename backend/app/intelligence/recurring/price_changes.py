"""Price change and amount shift detection for recurring commitments.

Follows docs/09_AI_INTELLIGENCE_ENGINE.md:
- Compare new payment to a robust historical baseline (median of earlier observations).
- Materiality threshold: absolute change >= ₹10.00 or percentage change >= 2.0%.
- Single increase flagged as "possible" (possible amount change), never assumed confirmed.
- Persistent shifts across >= 2 observations recorded with high evidence.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List
from backend.app.intelligence.recurring.amount_analysis import round_money


@dataclass
class DetectedPriceChange:
    """Detected price change event ready for persistence or display."""

    previous_amount: Decimal
    new_amount: Decimal
    absolute_change: Decimal
    percentage_change: Decimal
    effective_date: date
    status: str  # "possible", "confirmed_by_user", "dismissed"
    evidence: Dict[str, Any]


def detect_price_changes(
    observations: List[tuple[date, Decimal]],
    is_variable_bill: bool = False,
    min_absolute_threshold: Decimal = Decimal("10.00"),
    min_percentage_threshold: Decimal = Decimal("2.00"),
) -> List[DetectedPriceChange]:
    """Detect price change events chronologically across observations.

    Args:
        observations: List of (observed_date, amount) tuples sorted chronologically.
        is_variable_bill: Whether the commitment has variable amounts (e.g. electricity).
        min_absolute_threshold: Minimum absolute INR change to qualify (default ₹10.00).
        min_percentage_threshold: Minimum percentage change to qualify (default 2.0%).

    Returns:
        List of DetectedPriceChange instances.
    """
    if len(observations) < 2:
        return []

    # Sort observations chronologically
    sorted_obs = sorted(observations, key=lambda x: x[0])
    detected_changes: List[DetectedPriceChange] = []

    # Track distinct baseline amounts
    # Use earlier window median as baseline
    baseline_amounts: List[Decimal] = [sorted_obs[0][1]]

    for i in range(1, len(sorted_obs)):
        obs_date, current_amt = sorted_obs[i]

        # Calculate median of baseline so far
        sorted_baseline = sorted(baseline_amounts)
        m = len(sorted_baseline)
        if m % 2 == 1:
            baseline_amt = sorted_baseline[m // 2]
        else:
            baseline_amt = (sorted_baseline[m // 2 - 1] + sorted_baseline[m // 2]) / Decimal(2)

        baseline_amt = round_money(baseline_amt)

        # Check difference from baseline
        abs_diff = round_money(current_amt - baseline_amt)
        if baseline_amt > Decimal("0"):
            pct_diff = round_money((abs_diff / baseline_amt) * Decimal(100))
        else:
            pct_diff = Decimal("0.00")

        # Check materiality
        is_material = (
            abs(abs_diff) >= min_absolute_threshold
            or abs(pct_diff) >= min_percentage_threshold
        )

        if is_material and abs_diff != Decimal("0.00"):
            direction = "increase" if abs_diff > Decimal("0") else "decrease"
            # Check persistence: do subsequent observations also keep this new amount?
            remaining_obs = sorted_obs[i:]
            same_new_amt_count = sum(1 for _, amt in remaining_obs if amt == current_amt)
            persistent = same_new_amt_count >= 2

            evidence = {
                "change_type": f"price_{direction}",
                "baseline_amount": str(baseline_amt),
                "new_amount": str(current_amt),
                "absolute_change": str(abs_diff),
                "percentage_change": str(pct_diff),
                "observation_date": obs_date.isoformat(),
                "observations_evaluated": len(sorted_obs),
                "persistent": persistent,
                "is_variable_bill": is_variable_bill,
                "note": (
                    f"Possible {direction} of ₹{abs(abs_diff)} ({abs(pct_diff):.1f}%) "
                    f"detected on {obs_date.isoformat()}."
                    + (" Fluctuation typical of variable utilities." if is_variable_bill else "")
                ),
            }

            detected_changes.append(
                DetectedPriceChange(
                    previous_amount=baseline_amt,
                    new_amount=current_amt,
                    absolute_change=abs_diff,
                    percentage_change=pct_diff,
                    effective_date=obs_date,
                    status="possible",
                    evidence=evidence,
                )
            )

            # Reset baseline to new amount going forward
            baseline_amounts = [current_amt]
        else:
            baseline_amounts.append(current_amt)

    return detected_changes
