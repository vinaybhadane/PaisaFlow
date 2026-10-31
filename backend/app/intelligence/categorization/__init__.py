"""Categorization package."""

from backend.app.intelligence.categorization.classifier import (
    ClassificationResult,
    TransactionClassifier,
)
from backend.app.intelligence.categorization.confidence import CategorizationConfidence
from backend.app.intelligence.categorization.rules import (
    DeterministicCategorizationRules,
    RuleMatchResult,
)
from backend.app.intelligence.categorization.taxonomy import (
    TAXONOMY_SPEC,
    CategoryTaxonomyService,
)

__all__ = [
    "CategorizationConfidence",
    "CategoryTaxonomyService",
    "ClassificationResult",
    "DeterministicCategorizationRules",
    "RuleMatchResult",
    "TAXONOMY_SPEC",
    "TransactionClassifier",
]

