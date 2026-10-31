"""Date normalization and validation utility."""

from datetime import date, datetime
import re
from typing import Optional, Tuple


class DateNormalizer:
    """Normalizes arbitrary date strings into canonical datetime.date instances."""

    DATE_FORMATS = [
        # Day First formats (Common in India en-IN, UK)
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        # ISO formats
        "%Y-%m-%d",
        "%Y/%m/%d",
        # Textual month formats
        "%d %b %Y",
        "%d-%b-%Y",
        "%d %B %Y",
        "%d-%B-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        # Month First formats
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]

    @classmethod
    def normalize_date(cls, raw_date: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
        """Parse raw date string into canonical date.

        Returns:
            (canonical_date, error_message)
        """
        if not raw_date or not str(raw_date).strip():
            return None, "Empty date value"

        clean_str = re.sub(r"\s+", " ", str(raw_date).strip())

        # Strip timestamp portion if present (e.g. '2026-05-28 10:30:00' -> '2026-05-28')
        clean_str = clean_str.split(" ")[0] if " " in clean_str and ("-" in clean_str or "/" in clean_str) else clean_str

        for fmt in cls.DATE_FORMATS:
            try:
                dt = datetime.strptime(clean_str, fmt).date()
                # Sanity check: year must be reasonable (e.g. 1990 to 2100)
                if 1990 <= dt.year <= 2100:
                    return dt, None
            except ValueError:
                continue

        return None, f"Unrecognized or invalid date format: '{raw_date}'"

    @classmethod
    def normalize(cls, raw_date: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
        """Convenience alias for normalize_date."""
        return cls.normalize_date(raw_date)
