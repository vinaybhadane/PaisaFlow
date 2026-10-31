"""Merchant description cleaning and alias resolution."""

import re
from typing import Dict, Optional, Tuple


class MerchantNormalizer:
    """Cleans raw transaction descriptors and resolves aliases against canonical merchants."""

    # Common bank transaction prefixes to strip
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

    # Documented synthetic alias dictionary mapping aliases to canonical merchants
    SYNTHETIC_ALIASES = {
        "FRESH MART POS": "FRESHMART RETAIL",
        "FRESHMART HYPER": "FRESHMART RETAIL",
        "FRESHMART": "FRESHMART RETAIL",
        "MHR RENT": "METRO HOME RENT",
        "METRO PROPERTIES POS": "METRO HOME RENT",
        "METRO PROPERTIES": "METRO HOME RENT",
        "NSTAR ELEC": "NORTHSTAR UTILITIES",
        "NORTHSTAR POWER BILL": "NORTHSTAR UTILITIES",
        "NORTHSTAR POWER": "NORTHSTAR UTILITIES",
        "STREAMBOX SUB": "STREAMBOX MEDIA",
        "STREAMBOX DIGITAL": "STREAMBOX MEDIA",
        "STREAMBOX": "STREAMBOX MEDIA",
        "CITYRIDE APP": "CITYRIDE MOBILITY",
        "CR*MOBILITY": "CITYRIDE MOBILITY",
        "CITYRIDE": "CITYRIDE MOBILITY",
        "CLDNEST BILL": "CLOUDNEST STORAGE",
        "CLOUDNEST CLOUD": "CLOUDNEST STORAGE",
        "CLOUDNEST": "CLOUDNEST STORAGE",
        # Common commercial consumer brands
        "SWIGGY": "Swiggy",
        "BLINKIT": "Blinkit",
        "NETFLIX": "Netflix",
        "ZOMATO": "Zomato",
        "UBER": "Uber",
        "AMAZON": "Amazon",
        "AIRTEL": "Airtel",
        "STARBUCKS": "Starbucks",
        "GOOGLE": "Google",
        "MICROSOFT": "Microsoft",
        "SPOTIFY": "Spotify",
        "GITHUB": "GitHub",
    }

    @classmethod
    def clean_description(cls, raw_desc: str) -> str:
        """Strip noisy bank prefixes and normalize casing and whitespace."""
        if not raw_desc:
            return "Unspecified Transaction"

        text = raw_desc.strip()

        # Strip prefixes
        for pattern in cls.PREFIX_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Strip trailing reference IDs like '/10293847291' or '/CR' or '/DR'
        text = re.sub(r"/(?:CR|DR|[0-9]{6,})$", "", text, flags=re.IGNORECASE).strip()

        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip() or raw_desc.strip()

    @classmethod
    def resolve_merchant(
        cls,
        raw_description: str,
        custom_aliases: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, Optional[str]]:
        """Resolve cleaned description and identify canonical merchant name if an alias matches.

        Returns:
            (normalized_description, canonical_merchant_name_or_None)
        """
        cleaned = cls.clean_description(raw_description)
        normalized_key = cleaned.upper().strip()

        alias_map = cls.SYNTHETIC_ALIASES.copy()
        if custom_aliases:
            alias_map.update({k.upper(): v for k, v in custom_aliases.items()})

        # Exact alias match
        if normalized_key in alias_map:
            return cleaned.title(), alias_map[normalized_key]

        # Partial token match for known aliases
        for alias, canonical in alias_map.items():
            if alias in normalized_key:
                return cleaned.title(), canonical

        # No canonical alias resolved
        return cleaned.title(), None

    @classmethod
    def normalize(cls, raw_desc: str) -> Tuple[Optional[str], str]:
        """Convenience method returning (canonical_merchant, cleaned_description)."""
        cleaned, canonical = cls.resolve_merchant(raw_desc)
        return canonical, cleaned
