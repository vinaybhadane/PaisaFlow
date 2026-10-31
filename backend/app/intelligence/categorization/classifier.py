"""Hierarchical multi-tier transaction classifier coordinating rules, merchants, and user overrides."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.categorization.confidence import CategorizationConfidence
from backend.app.intelligence.categorization.rules import DeterministicCategorizationRules
from backend.app.intelligence.categorization.taxonomy import CategoryTaxonomyService
from backend.app.intelligence.merchant.resolver import MerchantResolutionResult, MerchantResolver
from backend.app.models.categorization_rule import CategorizationRule
from backend.app.models.category import Category


@dataclass
class ClassificationResult:
    """Complete categorization decision and provenance."""

    category_id: uuid.UUID
    category_name: str
    subcategory_id: Optional[uuid.UUID]
    subcategory_name: Optional[str]
    confidence: CategorizationConfidence
    resolved_merchant_name: Optional[str]
    resolution_method: str
    review_status: str  # 'confirmed' for high confidence, 'flagged' for review required


class TransactionClassifier:
    """Executes multi-tier transaction categorization."""

    def __init__(self, merchant_resolver: Optional[MerchantResolver] = None) -> None:
        self.merchant_resolver = merchant_resolver or MerchantResolver()

    async def classify(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        normalized_description: str,
        direction: str,
        transaction_type: str,
        user_rules: Optional[List[CategorizationRule]] = None,
        cached_categories: Optional[Dict[str, Category]] = None,
    ) -> ClassificationResult:
        """Categorize a transaction following strict precedence rules.

        Precedence:
        1. User-specific learned or defined rules
        2. Deterministic type rules (transfers, refunds)
        3. Merchant canonical category mapping
        4. Deterministic keyword and pattern rules
        5. Uncategorized fallback with review requirement
        """
        # Ensure category map is ready
        cat_map = cached_categories or await CategoryTaxonomyService.seed_system_categories(session)

        clean_desc = self.merchant_resolver.clean_description(normalized_description)
        desc_upper = clean_desc.upper()

        # Step 0: Resolve merchant candidates
        merchant_res: MerchantResolutionResult = self.merchant_resolver.resolve(normalized_description)
        resolved_merchant = merchant_res.canonical_name

        # ----------------------------------------------------------------------
        # TIER 1: User-Specific Categorization Rules
        # ----------------------------------------------------------------------
        if user_rules:
            for rule in sorted(user_rules, key=lambda r: r.priority, reverse=True):
                if not rule.is_active:
                    continue

                rule_matched = False
                scope_val = rule.scope_value or {}

                if rule.scope_type == "exact_merchant":
                    target_merchant = str(scope_val.get("merchant_name", "")).upper()
                    if resolved_merchant and resolved_merchant.upper() == target_merchant:
                        rule_matched = True
                    elif target_merchant and target_merchant in desc_upper:
                        rule_matched = True

                elif rule.scope_type == "merchant_alias":
                    pattern = str(scope_val.get("pattern", "")).upper()
                    if pattern and pattern in desc_upper:
                        rule_matched = True

                elif rule.scope_type == "description_contains":
                    substring = str(scope_val.get("substring", "")).upper()
                    if substring and substring in desc_upper:
                        rule_matched = True

                if rule_matched:
                    rule_cat = await CategoryTaxonomyService.get_by_id(session, rule.category_id)
                    rule_subcat = (
                        await CategoryTaxonomyService.get_by_id(session, rule.subcategory_id)
                        if rule.subcategory_id
                        else None
                    )
                    if rule_cat:
                        conf = CategorizationConfidence.calculate(
                            method="user_rule",
                            base_score=1.0,
                            evidence_tokens=[
                                f"User rule (ID: {str(rule.id)[:8]}) matched {rule.scope_type} with priority {rule.priority}"
                            ],
                        )
                        return ClassificationResult(
                            category_id=rule_cat.id,
                            category_name=rule_cat.name,
                            subcategory_id=rule_subcat.id if rule_subcat else None,
                            subcategory_name=rule_subcat.name if rule_subcat else None,
                            confidence=conf,
                            resolved_merchant_name=resolved_merchant,
                            resolution_method="user_rule",
                            review_status="confirmed",
                        )

        # ----------------------------------------------------------------------
        # TIER 2: Deterministic Transaction Type Overrides (Transfers & Refunds)
        # ----------------------------------------------------------------------
        if transaction_type == "transfer":
            parent = cat_map.get("Transfers") or await CategoryTaxonomyService.get_by_name(session, "Transfers")
            child = (
                cat_map.get("Own Account Transfer")
                if "OWN ACCT" in desc_upper
                else cat_map.get("Peer-to-Peer Transfer")
            )
            if parent:
                conf = CategorizationConfidence.calculate(
                    method="deterministic_type",
                    base_score=0.98,
                    evidence_tokens=["Classified as internal transfer; excluded from spending calculations"],
                )
                return ClassificationResult(
                    category_id=parent.id,
                    category_name=parent.name,
                    subcategory_id=child.id if child else None,
                    subcategory_name=child.name if child else None,
                    confidence=conf,
                    resolved_merchant_name=resolved_merchant,
                    resolution_method="deterministic_transfer",
                    review_status="confirmed",
                )

        if transaction_type == "refund":
            parent = cat_map.get("Refunds") or await CategoryTaxonomyService.get_by_name(session, "Refunds")
            child = cat_map.get("Merchant Refund")
            if parent:
                conf = CategorizationConfidence.calculate(
                    method="deterministic_type",
                    base_score=0.98,
                    evidence_tokens=["Classified as refund credit adjustment; isolated from regular income"],
                )
                return ClassificationResult(
                    category_id=parent.id,
                    category_name=parent.name,
                    subcategory_id=child.id if child else None,
                    subcategory_name=child.name if child else None,
                    confidence=conf,
                    resolved_merchant_name=resolved_merchant,
                    resolution_method="deterministic_refund",
                    review_status="confirmed",
                )

        # ----------------------------------------------------------------------
        # TIER 3: Merchant Canonical Category Mapping
        # ----------------------------------------------------------------------
        if merchant_res.canonical_name and merchant_res.category_hint:
            parent = cat_map.get(merchant_res.category_hint)
            child = cat_map.get(merchant_res.subcategory_hint) if merchant_res.subcategory_hint else None
            if parent:
                conf = CategorizationConfidence.calculate(
                    method=f"merchant_{merchant_res.method}",
                    base_score=merchant_res.confidence,
                    evidence_tokens=[
                        f"Resolved merchant '{merchant_res.canonical_name}' via {merchant_res.method}",
                        merchant_res.evidence,
                    ],
                )
                return ClassificationResult(
                    category_id=parent.id,
                    category_name=parent.name,
                    subcategory_id=child.id if child else None,
                    subcategory_name=child.name if child else None,
                    confidence=conf,
                    resolved_merchant_name=resolved_merchant,
                    resolution_method=f"merchant_{merchant_res.method}",
                    review_status="confirmed" if not conf.requires_review else "flagged",
                )

        # ----------------------------------------------------------------------
        # TIER 4: Deterministic Pattern & Keyword Rules
        # ----------------------------------------------------------------------
        rule_eval = DeterministicCategorizationRules.evaluate(
            normalized_description=normalized_description,
            direction=direction,
            transaction_type=transaction_type,
        )
        if rule_eval.matched:
            parent = cat_map.get(rule_eval.category_name)
            child = cat_map.get(rule_eval.subcategory_name) if rule_eval.subcategory_name else None
            if parent:
                conf = CategorizationConfidence.calculate(
                    method="pattern_rule",
                    base_score=rule_eval.confidence,
                    evidence_tokens=[rule_eval.evidence],
                )
                return ClassificationResult(
                    category_id=parent.id,
                    category_name=parent.name,
                    subcategory_id=child.id if child else None,
                    subcategory_name=child.name if child else None,
                    confidence=conf,
                    resolved_merchant_name=resolved_merchant,
                    resolution_method=rule_eval.rule_name,
                    review_status="confirmed",
                )

        # ----------------------------------------------------------------------
        # TIER 5: Fallback & Review-Required State
        # ----------------------------------------------------------------------
        if direction == "credit":
            parent = cat_map.get("Income") or await CategoryTaxonomyService.get_by_name(session, "Income")
            child = cat_map.get("Other Income")
            conf = CategorizationConfidence.calculate(
                method="direction_fallback",
                base_score=0.45,
                evidence_tokens=["Unrecognized credit transaction; flagged for user review"],
            )
        else:
            parent = cat_map.get("Other") or await CategoryTaxonomyService.get_by_name(session, "Other")
            child = cat_map.get("Uncategorized Expense")
            conf = CategorizationConfidence.calculate(
                method="uncategorized",
                base_score=0.20,
                evidence_tokens=["No recognized merchant or pattern rule matched descriptor"],
            )

        return ClassificationResult(
            category_id=parent.id,
            category_name=parent.name,
            subcategory_id=child.id if child else None,
            subcategory_name=child.name if child else None,
            confidence=conf,
            resolved_merchant_name=resolved_merchant,
            resolution_method="fallback_uncategorized",
            review_status="flagged",
        )
