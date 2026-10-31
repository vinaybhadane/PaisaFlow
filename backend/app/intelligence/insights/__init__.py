"""Financial insights and spending analysis package."""

from backend.app.intelligence.insights.insights_engine import FinancialInsight, InsightsEngine
from backend.app.intelligence.insights.spending_analyzer import (
    CategorySpendSummary,
    MerchantSpendSummary,
    MonthlyTrendItem,
    SpendingAnalysisResult,
    SpendingAnalyzer,
)

__all__ = [
    "CategorySpendSummary",
    "FinancialInsight",
    "InsightsEngine",
    "MerchantSpendSummary",
    "MonthlyTrendItem",
    "SpendingAnalysisResult",
    "SpendingAnalyzer",
]

