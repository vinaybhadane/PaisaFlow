"""Cadence detection and next expected date calculation.

Supports calendar-aware cadence identification:
- Weekly (~7 days, tolerance 5-9 days)
- Fortnightly (~14 days, tolerance 12-16 days)
- Monthly (calendar-aware, 26-35 days, tolerates month length variation and weekend shifts)
- Quarterly (~90 days / 3 months, tolerance 82-98 days)
- Half-yearly (~180 days / 6 months, tolerance 170-195 days)
- Yearly (~365 days / 12 months, tolerance 350-380 days)
- Custom / Irregular (when CV > 0.35 or non-standard intervals)
"""

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median, stdev
from typing import List, Optional
from dateutil.relativedelta import relativedelta


@dataclass
class CadenceAnalysisResult:
    """Result of cadence analysis across observation dates."""

    cadence: str  # weekly, fortnightly, monthly, quarterly, half_yearly, yearly, custom
    estimated_cadence_days: Optional[int]
    interval_days: List[int]
    median_interval: float
    mean_interval: float
    interval_cv: float  # Coefficient of variation (std / mean)
    is_regular: bool
    next_expected_date: Optional[date]
    last_observed_date: Optional[date]
    observation_count: int
    cadence_confidence: str  # high, medium, low
    cadence_rationale: str


def detect_cadence(dates: List[date]) -> CadenceAnalysisResult:
    """Detect the recurring cadence from a list of transaction dates.

    Args:
        dates: List of observation dates (can be unsorted).

    Returns:
        CadenceAnalysisResult with cadence, interval statistics, and next expected date.
    """
    if not dates:
        return CadenceAnalysisResult(
            cadence="custom",
            estimated_cadence_days=None,
            interval_days=[],
            median_interval=0.0,
            mean_interval=0.0,
            interval_cv=0.0,
            is_regular=False,
            next_expected_date=None,
            last_observed_date=None,
            observation_count=0,
            cadence_confidence="low",
            cadence_rationale="No observation dates provided.",
        )

    # Sort dates ascending and deduplicate within the same day
    sorted_unique_dates = sorted(list(set(dates)))
    n = len(sorted_unique_dates)
    last_date = sorted_unique_dates[-1]

    if n < 2:
        return CadenceAnalysisResult(
            cadence="custom",
            estimated_cadence_days=None,
            interval_days=[],
            median_interval=0.0,
            mean_interval=0.0,
            interval_cv=0.0,
            is_regular=False,
            next_expected_date=None,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence="low",
            cadence_rationale="At least 2 distinct observation dates required to establish cadence.",
        )

    # Calculate intervals in days
    intervals: List[int] = [
        (sorted_unique_dates[i + 1] - sorted_unique_dates[i]).days
        for i in range(n - 1)
    ]

    med_gap = float(median(intervals))
    avg_gap = float(mean(intervals))
    std_gap = float(stdev(intervals)) if len(intervals) > 1 else 0.0
    cv = (std_gap / avg_gap) if avg_gap > 0 else 0.0

    # Calculate calendar-aware month deltas
    month_deltas: List[int] = []
    day_diffs: List[int] = []
    for i in range(n - 1):
        d1 = sorted_unique_dates[i]
        d2 = sorted_unique_dates[i + 1]
        m_delta = (d2.year - d1.year) * 12 + (d2.month - d1.month)
        month_deltas.append(m_delta)
        day_diffs.append(abs(d2.day - d1.day))

    # Evaluate cadences against tolerances
    # 1. Weekly: ~7 days (range 5-9 days)
    if all(5 <= gap <= 9 for gap in intervals) or (5.5 <= med_gap <= 8.5 and cv <= 0.25):
        next_date = last_date + timedelta(days=7)
        conf = "high" if n >= 3 and cv <= 0.15 else "medium" if n >= 3 else "low"
        return CadenceAnalysisResult(
            cadence="weekly",
            estimated_cadence_days=7,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Consistent weekly pattern across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 2. Fortnightly: ~14 days (range 12-16 days)
    if all(12 <= gap <= 16 for gap in intervals) or (12.5 <= med_gap <= 15.5 and cv <= 0.25):
        next_date = last_date + timedelta(days=14)
        conf = "high" if n >= 3 and cv <= 0.15 else "medium" if n >= 3 else "low"
        return CadenceAnalysisResult(
            cadence="fortnightly",
            estimated_cadence_days=14,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Consistent fortnightly pattern across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 3. Monthly: calendar-aware check
    # Check if month deltas are consistently 1 (with at most 1 missed month where m_delta == 2)
    is_calendar_monthly = (
        all(m in (1, 2) for m in month_deltas)
        and sum(1 for m in month_deltas if m == 1) >= (len(month_deltas) * 0.7)
        and (all(d <= 5 for d in day_diffs) or (26 <= med_gap <= 35 and cv <= 0.30))
    )
    if is_calendar_monthly or (26 <= med_gap <= 35 and cv <= 0.30):
        # Determine anchor day of month from median of observed days
        observed_days = [d.day for d in sorted_unique_dates]
        anchor_day = int(median(observed_days))

        # Add 1 month using relativedelta
        # If last payment had a slight weekend shift, target the anchor day in the next month
        next_month_candidate = last_date + relativedelta(months=1)
        try:
            next_date = next_month_candidate.replace(day=min(anchor_day, 28))
            # If the month has more days and anchor is higher, clamp cleanly
            # relativedelta with day handles clamp safely:
            next_date = last_date + relativedelta(months=1, day=anchor_day)
        except (ValueError, OverflowError):
            next_date = last_date + relativedelta(months=1)

        conf = "high" if n >= 3 and cv <= 0.20 else "medium" if n >= 3 else "low"
        return CadenceAnalysisResult(
            cadence="monthly",
            estimated_cadence_days=30,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Calendar-aware monthly pattern across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 4. Quarterly: ~90 days / 3 months (range 82-98 days or month deltas ~3)
    is_calendar_quarterly = (
        all(m in (3, 4) for m in month_deltas) or (82 <= med_gap <= 98 and cv <= 0.25)
    )
    if is_calendar_quarterly:
        next_date = last_date + relativedelta(months=3)
        conf = "high" if n >= 3 and cv <= 0.15 else "medium" if n >= 2 else "low"
        return CadenceAnalysisResult(
            cadence="quarterly",
            estimated_cadence_days=91,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Quarterly cadence detected across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 5. Half-yearly: ~180 days / 6 months (range 170-195 days or month deltas ~6)
    is_calendar_half_yearly = (
        all(m in (5, 6, 7) for m in month_deltas) or (170 <= med_gap <= 195 and cv <= 0.25)
    )
    if is_calendar_half_yearly:
        next_date = last_date + relativedelta(months=6)
        conf = "medium" if n >= 2 else "low"
        return CadenceAnalysisResult(
            cadence="half_yearly",
            estimated_cadence_days=182,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Half-yearly cadence detected across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 6. Yearly: ~365 days / 12 months (range 350-380 days or month deltas ~12)
    is_calendar_yearly = (
        all(m in (11, 12, 13) for m in month_deltas) or (350 <= med_gap <= 380 and cv <= 0.20)
    )
    if is_calendar_yearly:
        next_date = last_date + relativedelta(years=1)
        conf = "medium" if n >= 2 else "low"
        return CadenceAnalysisResult(
            cadence="yearly",
            estimated_cadence_days=365,
            interval_days=intervals,
            median_interval=med_gap,
            mean_interval=avg_gap,
            interval_cv=round(cv, 4),
            is_regular=True,
            next_expected_date=next_date,
            last_observed_date=last_date,
            observation_count=n,
            cadence_confidence=conf,
            cadence_rationale=f"Yearly cadence detected across {n} observations (median gap {med_gap:.1f} days).",
        )

    # 7. Irregular / Custom:
    # High variance (CV > 0.35) or no standard cadence match
    # Strict rule: "Irregular candidates need more evidence and should not receive an invented next date."
    return CadenceAnalysisResult(
        cadence="custom",
        estimated_cadence_days=int(round(med_gap)) if med_gap > 0 else None,
        interval_days=intervals,
        median_interval=med_gap,
        mean_interval=avg_gap,
        interval_cv=round(cv, 4),
        is_regular=False,
        next_expected_date=None,  # Do not invent next expected date for irregular patterns
        last_observed_date=last_date,
        observation_count=n,
        cadence_confidence="low",
        cadence_rationale=(
            f"Intervals are irregular (CV: {cv:.2f} > 0.35, median gap {med_gap:.1f} days). "
            "No standard cadence matched. Next expected date withheld to prevent false expectation."
        ),
    )
