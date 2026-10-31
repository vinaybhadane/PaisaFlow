"""Merchant resolution engine implementing exact, token, and fuzzy matching."""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

from backend.app.intelligence.merchant.aliases import KNOWN_MERCHANTS_CATALOGUE


@dataclass
class MerchantResolutionResult:
    """Structured resolution outcome for a transaction description."""

    canonical_name: Optional[str]
    cleaned_description: str
    confidence: float
    method: str  # exact_alias, normalized_exact, token_match, fuzzy_match, unresolved
    category_hint: Optional[str] = None
    subcategory_hint: Optional[str] = None
    is_unknown: bool = False
    evidence: str = ""


class MerchantResolver:
    """Resolves noisy financial transaction descriptors to canonical merchant records."""

    PREFIX_PATTERNS = [
        r"^(?:UPI/|UPI-|UPI\s+)",
        r"^(?:POS/|POS\s+|POS-)",
        r"^(?:NEFT/|NEFT-|NEFT\s+CR\s+|NEFT\s+DR\s+)",
        r"^(?:IMPS/|IMPS-|IMPS\s+)",
        r"^(?:RTGS/|RTGS-|RTGS\s+)",
        r"^(?:ACH/|ACH-|ACH\s+)",
        r"^(?:DEBIT\s+CARD-|DEBIT\s+CARD\s+)",
        r"^(?:ATM\s+WDL-|ATM\s+WDL\s+)",
        r"^(?:BILLDESK\*|PAYTM\*|RAZORPAY\*|CCAVENUE\*)",
    ]

    def __init__(self, custom_catalogue: Optional[List[Dict[str, Any]]] = None) -> None:
        self.catalogue = custom_catalogue or KNOWN_MERCHANTS_CATALOGUE
        self._build_index()

    def _build_index(self) -> None:
        """Construct fast lookup index from alias patterns to canonical merchants."""
        self.exact_alias_index: Dict[str, Dict[str, Any]] = {}
        self.all_canonical_names: List[str] = []

        for item in self.catalogue:
            canon = item["canonical_name"]
            self.all_canonical_names.append(canon)
            # Index canonical name itself
            self.exact_alias_index[canon.upper()] = item

            # Index every declared alias
            for alias in item.get("aliases", []):
                self.exact_alias_index[alias.upper()] = item

    @classmethod
    def clean_description(cls, raw_desc: str) -> str:
        """Strip transaction channel prefixes, reference numbers, and redundant spaces."""
        if not raw_desc or not raw_desc.strip():
            return "Unspecified Transaction"

        text = raw_desc.strip()

        # Remove channel prefixes
        for pattern in cls.PREFIX_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Strip trailing bank reference suffixes e.g. /10293847291 or /CR or /DR
        text = re.sub(r"/(?:CR|DR|[0-9]{6,})$", "", text, flags=re.IGNORECASE).strip()

        # Strip trailing VPA suffixes e.g. @icici, @okhdfcbank
        text = re.sub(r"@[a-zA-Z0-9]+$", "", text).strip()

        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text or raw_desc.strip()

    def resolve(self, raw_description: str) -> MerchantResolutionResult:
        """Execute multi-tier deterministic and fuzzy merchant resolution.

        Tiers:
        1. Exact alias match
        2. Normalized descriptor exact match
        3. Word/token boundary match
        4. RapidFuzz token_sort_ratio match with collision margin protection
        5. Unresolved fallback
        """
        cleaned = self.clean_description(raw_description)
        norm_key = cleaned.upper().strip()

        # 1. Exact alias lookup
        if norm_key in self.exact_alias_index:
            entry = self.exact_alias_index[norm_key]
            return MerchantResolutionResult(
                canonical_name=entry["canonical_name"],
                cleaned_description=cleaned,
                confidence=0.98,
                method="exact_alias",
                category_hint=entry.get("category"),
                subcategory_hint=entry.get("subcategory"),
                is_unknown=False,
                evidence=f"Exact alias match for '{norm_key}'",
            )

        # 2. Token boundary match (look for exact merchant tokens within the descriptor)
        for alias_upper, entry in self.exact_alias_index.items():
            if len(alias_upper) >= 4:
                # Require word boundaries so 'BER' does not match 'UBER'
                pattern = rf"(?:\b|_){re.escape(alias_upper)}(?:\b|_)"
                if re.search(pattern, norm_key):
                    return MerchantResolutionResult(
                        canonical_name=entry["canonical_name"],
                        cleaned_description=cleaned,
                        confidence=0.92,
                        method="token_match",
                        category_hint=entry.get("category"),
                        subcategory_hint=entry.get("subcategory"),
                        is_unknown=False,
                        evidence=f"Token boundary match for '{alias_upper}' in '{norm_key}'",
                    )

        # 3. Fuzzy matching with RapidFuzz
        candidates: List[Tuple[float, Dict[str, Any]]] = []
        for alias_upper, entry in self.exact_alias_index.items():
            score = fuzz.token_sort_ratio(norm_key, alias_upper)
            if score >= 80.0:
                candidates.append((score, entry))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if candidates:
            best_score, best_entry = candidates[0]
            # Collision prevention: check margin over second-best candidate
            has_margin = True
            if len(candidates) > 1:
                second_score, second_entry = candidates[1]
                if second_entry["canonical_name"] != best_entry["canonical_name"]:
                    if (best_score - second_score) < 10.0:
                        has_margin = False

            if best_score >= 85.0 and has_margin:
                normalized_conf = round(best_score / 100.0 * 0.9, 2)
                return MerchantResolutionResult(
                    canonical_name=best_entry["canonical_name"],
                    cleaned_description=cleaned,
                    confidence=normalized_conf,
                    method="fuzzy_match",
                    category_hint=best_entry.get("category"),
                    subcategory_hint=best_entry.get("subcategory"),
                    is_unknown=False,
                    evidence=f"Fuzzy match (score: {best_score:.1f}) against '{best_entry['canonical_name']}'",
                )

        # 4. Unresolved fallback
        return MerchantResolutionResult(
            canonical_name=None,
            cleaned_description=cleaned,
            confidence=0.20,
            method="unresolved",
            category_hint=None,
            subcategory_hint=None,
            is_unknown=True,
            evidence="No matching merchant alias or token identified",
        )
