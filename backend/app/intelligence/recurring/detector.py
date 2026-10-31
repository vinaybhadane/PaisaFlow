"""Recurring payment detection engine.

Analyzes transaction history to identify recurring subscriptions, bills, rent,
utilities, loan repayments, and recurring income patterns.

Core rules (from docs/09_AI_INTELLIGENCE_ENGINE.md and AGENTS.md):
- Group candidates by resolved merchant, account, direction, and currency.
- Exclude own-account transfers, refunds, and excluded rows.
- 1 observation CANNOT establish recurrence.
- 2 observations create a provisional candidate (confidence='low', status='likely').
- >= 3 observations create a full candidate (confidence='high' or 'medium').
- Irregular intervals (CV > 0.35) marked 'custom' with no next expected date.
- All monetary arithmetic uses Python Decimal.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from backend.app.intelligence.recurring.amount_analysis import analyze_amounts
from backend.app.intelligence.recurring.cadence import detect_cadence
from backend.app.intelligence.recurring.price_changes import detect_price_changes, DetectedPriceChange


@dataclass
class RecurringObservationRecord:
    """Record of an individual observation for a recurring candidate."""

    transaction_id: uuid.UUID
    observed_date: date
    observed_amount: Decimal


@dataclass
class DetectedCommitmentCandidate:
    """Fully analyzed recurring commitment candidate."""

    display_name: str
    direction: str  # debit or credit
    cadence: str  # weekly, fortnightly, monthly, quarterly, half_yearly, yearly, custom
    estimated_cadence_days: Optional[int]
    typical_amount: Decimal
    min_amount: Optional[Decimal]
    max_amount: Optional[Decimal]
    currency: str
    confidence: str  # high, medium, low
    status: str  # likely, confirmed, rejected, review_required
    last_observed_date: Optional[date]
    next_expected_date: Optional[date]
    merchant_id: Optional[uuid.UUID]
    observations: List[RecurringObservationRecord] = field(default_factory=list)
    price_changes: List[DetectedPriceChange] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


class RecurringDetector:
    """Detection engine for identifying recurring financial patterns."""

    def detect_candidates_from_transactions(
        self, transactions: List[Any]
    ) -> List[DetectedCommitmentCandidate]:
        """Analyze a list of transaction models/objects and detect recurring patterns.

        Args:
            transactions: List of Transaction database model instances or dicts.

        Returns:
            List of DetectedCommitmentCandidate instances.
        """
        # 1. Filter out non-eligible transactions
        eligible_txs = []
        for tx in transactions:
            is_excluded = getattr(tx, "is_excluded", False)
            tx_type = getattr(tx, "transaction_type", "expense")
            if is_excluded or tx_type in ("transfer", "refund"):
                continue

            amt = getattr(tx, "amount", Decimal("0.00"))
            if amt <= Decimal("0.00"):
                continue

            eligible_txs.append(tx)

        # 2. Group transactions into candidate clusters
        groups: Dict[tuple, List[Any]] = {}
        for tx in eligible_txs:
            direction = getattr(tx, "direction", "debit")
            currency = getattr(tx, "currency", "INR")
            merchant_id = getattr(tx, "merchant_id", None)
            norm_desc = (getattr(tx, "normalized_description", "") or "").strip().lower()

            if merchant_id is not None:
                group_key = (direction, currency, "merchant", str(merchant_id))
            else:
                # Group by normalized description tokens or clean name
                clean_key = norm_desc if norm_desc else "unknown"
                group_key = (direction, currency, "name", clean_key)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(tx)

        candidates: List[DetectedCommitmentCandidate] = []

        # 3. Analyze each group
        for group_key, tx_list in groups.items():
            direction, currency, key_type, key_val = group_key

            # At least 2 observations required to consider recurrence
            if len(tx_list) < 2:
                continue

            # Sort chronologically
            sorted_txs = sorted(tx_list, key=lambda t: getattr(t, "transaction_date"))

            dates = [getattr(t, "transaction_date") for t in sorted_txs]
            amounts = [getattr(t, "amount") for t in sorted_txs]

            # Run Cadence Analysis
            cadence_res = detect_cadence(dates)

            # If cadence detection found no viable interval pattern (e.g. all on the exact same date)
            if not cadence_res.is_regular and cadence_res.interval_cv > 0.40 and len(tx_list) < 3:
                # 2 sporadic transactions with completely irregular timing are not recurring
                continue

            # Run Amount Analysis
            amount_res = analyze_amounts(
                amounts, cadence_res.cadence, cadence_res.estimated_cadence_days
            )

            # Run Price Change Detection
            obs_tuples = [
                (getattr(t, "transaction_date"), getattr(t, "amount")) for t in sorted_txs
            ]
            price_changes = detect_price_changes(
                obs_tuples, is_variable_bill=(amount_res.stability == "variable")
            )

            # Determine display name and merchant
            first_tx = sorted_txs[0]
            merchant_id_val = getattr(first_tx, "merchant_id", None)
            merchant_rel = getattr(first_tx, "merchant", None)

            if merchant_rel is not None and getattr(merchant_rel, "display_name", None):
                display_name = merchant_rel.display_name
            elif getattr(first_tx, "merchant_name", None):
                display_name = first_tx.merchant_name
            else:
                raw_name = getattr(first_tx, "normalized_description", "Recurring Commitment")
                display_name = " ".join(word.capitalize() for word in raw_name.split())

            # Calibrate overall confidence
            if len(sorted_txs) == 2:
                overall_confidence = "low"
            elif cadence_res.is_regular and amount_res.stability == "stable" and len(sorted_txs) >= 3:
                overall_confidence = "high"
            elif cadence_res.is_regular and len(sorted_txs) >= 3:
                overall_confidence = "medium"
            else:
                overall_confidence = "low"

            # Create observation records
            observation_records = [
                RecurringObservationRecord(
                    transaction_id=getattr(t, "id"),
                    observed_date=getattr(t, "transaction_date"),
                    observed_amount=getattr(t, "amount"),
                )
                for t in sorted_txs
            ]

            evidence = {
                "observation_count": len(sorted_txs),
                "cadence_rationale": cadence_res.cadence_rationale,
                "interval_median_days": cadence_res.median_interval,
                "interval_cv": cadence_res.interval_cv,
                "amount_stability": amount_res.stability,
                "spread_percentage": str(amount_res.spread_percentage),
                "monthly_planning_equivalent": str(amount_res.monthly_equivalent),
                "estimated_annual_cost": str(amount_res.estimated_annual_cost),
                "detected_price_changes_count": len(price_changes),
                "first_observed_date": sorted_txs[0].transaction_date.isoformat(),
                "last_observed_date": sorted_txs[-1].transaction_date.isoformat(),
            }

            candidates.append(
                DetectedCommitmentCandidate(
                    display_name=display_name,
                    direction=direction,
                    cadence=cadence_res.cadence,
                    estimated_cadence_days=cadence_res.estimated_cadence_days,
                    typical_amount=amount_res.typical_amount,
                    min_amount=amount_res.min_amount,
                    max_amount=amount_res.max_amount,
                    currency=currency,
                    confidence=overall_confidence,
                    status="likely",
                    last_observed_date=cadence_res.last_observed_date,
                    next_expected_date=cadence_res.next_expected_date,
                    merchant_id=merchant_id_val,
                    observations=observation_records,
                    price_changes=price_changes,
                    evidence=evidence,
                )
            )

        return candidates

