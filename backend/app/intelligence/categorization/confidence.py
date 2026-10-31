"""Confidence scoring, threshold calibration, and explainable evidence generation."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CategorizationConfidence:
    """Explainable confidence evaluation for a categorization outcome."""

    score: float  # Normalized between 0.0 and 1.0
    level: str  # 'high', 'medium', 'low'
    method: str  # 'user_rule', 'merchant_alias', 'deterministic_rule', 'fuzzy_match', 'fallback'
    requires_review: bool
    evidence: List[str] = field(default_factory=list)

    @classmethod
    def calculate(
        cls,
        method: str,
        base_score: float,
        evidence_tokens: List[str],
    ) -> "CategorizationConfidence":
        """Compute calibrated confidence score, review requirement, and categorical level."""
        score = max(0.0, min(1.0, round(base_score, 2)))

        if score >= 0.80:
            level = "high"
            requires_review = False
        elif score >= 0.50:
            level = "medium"
            requires_review = True
        else:
            level = "low"
            requires_review = True

        return cls(
            score=score,
            level=level,
            method=method,
            requires_review=requires_review,
            evidence=evidence_tokens,
        )

