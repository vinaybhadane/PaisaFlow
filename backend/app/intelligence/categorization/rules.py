"""Deterministic pattern and keyword-based categorization rules."""

from dataclasses import dataclass
import re
from typing import List, Optional, Tuple


@dataclass
class RuleMatchResult:
    """Outcome of a deterministic rule evaluation."""

    matched: bool
    category_name: str
    subcategory_name: Optional[str]
    confidence: float
    rule_name: str
    evidence: str


class DeterministicCategorizationRules:
    """Evaluates high-confidence deterministic pattern rules on normalized transactions."""

    # Keywords with mapped category, subcategory, and rule identifier
    PATTERNS: List[Tuple[str, str, Optional[str], str]] = [
        # Transfers
        (r"\b(?:TRF TO OWN ACCT|OWN ACCT|SELF TRANSFER|INTERNAL TRANSFER)\b", "Transfers", "Own Account Transfer", "rule_own_account_transfer"),
        (r"\b(?:CREDIT CARD BILL|CC PAYMENT|CARD AUTOPAY|CREDIT CARD PMT)\b", "Transfers", "Credit Card Bill Payment", "rule_cc_bill_payment"),
        (r"\b(?:TRF TO|TRF FROM|TRANSFER TO|TRANSFER FROM)\b", "Transfers", "Peer-to-Peer Transfer", "rule_general_transfer"),

        # Refunds & Cashbacks
        (r"\b(?:REFUND|REVERSAL|RTN|RETURNED)\b", "Refunds", "Merchant Refund", "rule_merchant_refund"),
        (r"\b(?:CASHBACK|REBATE|CASH REWARD)\b", "Refunds", "Cashback & Rebates", "rule_cashback"),

        # Income
        (r"\b(?:SALARY|PAYROLL|STIPEND|DIRECT DEP|WAGES)\b", "Income", "Salary", "rule_salary_income"),
        (r"\b(?:CLIENT PAYMENT|INVOICE PAYMENT|CONSULTING FEE)\b", "Income", "Freelance & Invoicing", "rule_freelance_income"),
        (r"\b(?:INTEREST CREDIT|SAVINGS INT|BANK INTEREST)\b", "Income", "Interest & Rewards", "rule_interest_income"),
        (r"\b(?:DIVIDEND|DIVIDEND CREDIT)\b", "Income", "Investments & Dividends", "rule_dividend_income"),

        # Housing & Rent
        (r"\b(?:HOUSE RENT|APARTMENT RENT|METRO HOME RENT|MHR RENT|FLAT RENT|LANDLORD)\b", "Housing & Rent", "Rent", "rule_rent_payment"),
        (r"\b(?:SOCIETY MAINT|MAINTENANCE CHARGE|MAINTENANCE FEE)\b", "Housing & Rent", "Maintenance & Society", "rule_society_maintenance"),

        # Utilities
        (r"\b(?:ELECTRICITY|POWER BILL|BESCOM|TATA POWER|NORTHSTAR UTILITIES|NSTAR ELEC)\b", "Utilities", "Electricity", "rule_electricity"),
        (r"\b(?:WATER BILL|WATER SUPPLY|JAL BOARD)\b", "Utilities", "Water", "rule_water_utility"),
        (r"\b(?:PIPED GAS|LPG GAS|INDANE|BHARAT GAS)\b", "Utilities", "Gas & Fuel", "rule_gas_utility"),
        (r"\b(?:BROADBAND|FIBER|AIRTEL FIBER|JIO FIBER|ACT FIBERNET|MOBILE RECHARGE)\b", "Utilities", "Broadband & Mobile", "rule_telecom_utility"),

        # Food & Dining
        (r"\b(?:BLINKIT|ZEPTO|INSTAMART|BIGBASKET|FRESHMART|SUPERMARKET|GROCERY|VEGETABLES)\b", "Food & Dining", "Groceries", "rule_groceries"),
        (r"\b(?:SWIGGY|ZOMATO|FOOD DELIVERY|EATS)\b", "Food & Dining", "Food Delivery", "rule_food_delivery"),
        (r"\b(?:STARBUCKS|CAFE|COFFEE|RESTAURANT|DINER|BAKERY|BISTRO)\b", "Food & Dining", "Restaurants & Cafes", "rule_dining_out"),

        # Transportation
        (r"\b(?:UBER|OLA CABS|CITYRIDE|RIDE HAILING|TAXI|AUTO RICKSHAW)\b", "Transportation", "Ride Hailing & Taxi", "rule_ride_hailing"),
        (r"\b(?:METRO RAIL|SUBWAY|BUS TICKET|LOCAL TRAIN)\b", "Transportation", "Public Transit", "rule_public_transit"),
        (r"\b(?:FASTAG|PETROL|DIESEL|HPCL|BPCL|IOCL|FUEL)\b", "Transportation", "Fuel & Fastag", "rule_fuel"),

        # Subscriptions & Entertainment
        (r"\b(?:NETFLIX|SPOTIFY|STREAMBOX|PRIME VIDEO|HOTSTAR|YOUTUBE PREMIUM)\b", "Entertainment & Subscriptions", "Streaming Services", "rule_streaming"),
        (r"\b(?:CLOUDNEST|GOOGLE STORAGE|GOOGLE ONE|MICROSOFT 365|GITHUB COPILOT|AWS|AZURE)\b", "Entertainment & Subscriptions", "Software & Cloud Storage", "rule_cloud_software"),
        (r"\b(?:BOOKMYSHOW|CINEMA|PVR|INOX|CONCERT)\b", "Entertainment & Subscriptions", "Movies & Events", "rule_movies_events"),

        # Healthcare
        (r"\b(?:PHARMACY|APOLLO|1MG|MEDPLUS|DRUGS|MEDICINES)\b", "Healthcare", "Pharmacy & Medicines", "rule_pharmacy"),
        (r"\b(?:HOSPITAL|CLINIC|CONSULTATION|DOCTOR|DENTAL)\b", "Healthcare", "Doctor & Clinic", "rule_doctor"),

        # Financial Charges
        (r"\b(?:ANNUAL FEE|MAINTENANCE FEE|SMS CHARGE|DEBIT CARD FEE|OVERDRAFT)\b", "Financial Charges", "Bank Charges & Fees", "rule_bank_charges"),
        (r"\b(?:LATE FEE|PENALTY CHARGE)\b", "Financial Charges", "Late Payment Penalty", "rule_late_penalty"),

        # Investments
        (r"\b(?:ZERODHA|GROWW|UPSTOX|MUTUAL FUND|SIP INSTALMENT|PPF DEPOSIT)\b", "Investments", "Mutual Funds & SIP", "rule_investments"),
    ]

    @classmethod
    def evaluate(
        cls,
        normalized_description: str,
        direction: str,
        transaction_type: str,
    ) -> RuleMatchResult:
        """Evaluate deterministic rules against transaction context."""
        text = normalized_description.upper().strip()

        # 1. Enforce strict type priorities
        if transaction_type == "transfer":
            return RuleMatchResult(
                matched=True,
                category_name="Transfers",
                subcategory_name="Own Account Transfer" if "OWN ACCT" in text else "Peer-to-Peer Transfer",
                confidence=0.98,
                rule_name="rule_type_transfer",
                evidence="Transaction classified as internal transfer; excluded from spending",
            )

        if transaction_type == "refund":
            return RuleMatchResult(
                matched=True,
                category_name="Refunds",
                subcategory_name="Merchant Refund",
                confidence=0.98,
                rule_name="rule_type_refund",
                evidence="Transaction classified as refund adjustment",
            )

        # 2. Pattern scan
        for pattern, parent_cat, child_cat, rule_id in cls.PATTERNS:
            if re.search(pattern, text):
                # Ensure direction compatibility (e.g. Salary must be credit, Rent must be debit)
                if parent_cat == "Income" and direction != "credit":
                    continue
                if parent_cat in ("Housing & Rent", "Utilities", "Food & Dining", "Shopping", "Transportation") and direction == "credit":
                    # Credit to expense category is likely a refund or adjustment
                    continue

                return RuleMatchResult(
                    matched=True,
                    category_name=parent_cat,
                    subcategory_name=child_cat,
                    confidence=0.90,
                    rule_name=rule_id,
                    evidence=f"Matched deterministic keyword rule '{rule_id}'",
                )

        return RuleMatchResult(
            matched=False,
            category_name="Other",
            subcategory_name="Uncategorized Expense",
            confidence=0.0,
            rule_name="none",
            evidence="No deterministic pattern matched",
        )

