"""Canonical merchant catalogue and alias definitions for synthetic Indian banking data."""

from typing import Any, Dict, List

# Structured catalogue of known synthetic merchants
# Each entry defines: canonical_name, category_name, subcategory_name, and alias_patterns
KNOWN_MERCHANTS_CATALOGUE: List[Dict[str, Any]] = [
    {
        "canonical_name": "Swiggy",
        "category": "Food & Dining",
        "subcategory": "Food Delivery",
        "aliases": [
            "SWIGGY",
            "SWIGGY INSTAMART",
            "BUNDL TECHNOLOGIES",
            "UPI-SWIGGY",
            "SWIGGY FOOD DELIVERY",
        ],
    },
    {
        "canonical_name": "Zomato",
        "category": "Food & Dining",
        "subcategory": "Food Delivery",
        "aliases": [
            "ZOMATO",
            "ZOMATO RESTAURANTS PVT",
            "ZOMATO MEDIA",
            "UPI-ZOMATO",
        ],
    },
    {
        "canonical_name": "Blinkit",
        "category": "Food & Dining",
        "subcategory": "Groceries",
        "aliases": [
            "BLINKIT",
            "BLINKIT ORDER",
            "BLINK COMMERCE",
            "GROFERS",
        ],
    },
    {
        "canonical_name": "Zepto",
        "category": "Food & Dining",
        "subcategory": "Groceries",
        "aliases": [
            "ZEPTO",
            "KIRANAKART",
            "ZEPTO QUICK",
        ],
    },
    {
        "canonical_name": "Freshmart Retail",
        "category": "Food & Dining",
        "subcategory": "Groceries",
        "aliases": [
            "FRESH MART POS",
            "FRESHMART HYPER",
            "FRESHMART",
            "FRESHMART RETAIL",
        ],
    },
    {
        "canonical_name": "Netflix",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Streaming Services",
        "aliases": [
            "NETFLIX",
            "NETFLIX MUMBAI IN",
            "NETFLIX ENTERTAINMENT IN",
            "NETFLIX INDIA",
        ],
    },
    {
        "canonical_name": "Spotify",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Streaming Services",
        "aliases": [
            "SPOTIFY",
            "SPOTIFY INDIA",
            "SPOTIFY AB",
            "SPOTIFY PREMIUM",
        ],
    },
    {
        "canonical_name": "Streambox Media",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Streaming Services",
        "aliases": [
            "STREAMBOX SUB",
            "STREAMBOX DIGITAL",
            "STREAMBOX",
            "STREAMBOX MEDIA",
        ],
    },
    {
        "canonical_name": "Cloudnest Storage",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Software & Cloud Storage",
        "aliases": [
            "CLDNEST BILL",
            "CLOUDNEST CLOUD",
            "CLOUDNEST",
            "CLOUDNEST STORAGE",
        ],
    },
    {
        "canonical_name": "Uber",
        "category": "Transportation",
        "subcategory": "Ride Hailing & Taxi",
        "aliases": [
            "UBER",
            "UBER INDIA RIDES",
            "UBER TRIP",
            "UBER RIDES",
        ],
    },
    {
        "canonical_name": "Ola Cabs",
        "category": "Transportation",
        "subcategory": "Ride Hailing & Taxi",
        "aliases": [
            "OLA CABS",
            "ANI TECHNOLOGIES",
            "OLA RIDE",
        ],
    },
    {
        "canonical_name": "Cityride Mobility",
        "category": "Transportation",
        "subcategory": "Ride Hailing & Taxi",
        "aliases": [
            "CITYRIDE APP",
            "CR*MOBILITY",
            "CITYRIDE",
            "CITYRIDE MOBILITY",
        ],
    },
    {
        "canonical_name": "Metro Home Rent",
        "category": "Housing & Rent",
        "subcategory": "Rent",
        "aliases": [
            "MHR RENT",
            "METRO PROPERTIES POS",
            "METRO PROPERTIES",
            "METRO HOME RENT",
        ],
    },
    {
        "canonical_name": "Northstar Utilities",
        "category": "Utilities",
        "subcategory": "Electricity",
        "aliases": [
            "NSTAR ELEC",
            "NORTHSTAR POWER BILL",
            "NORTHSTAR POWER",
            "NORTHSTAR UTILITIES",
        ],
    },
    {
        "canonical_name": "Tata Power",
        "category": "Utilities",
        "subcategory": "Electricity",
        "aliases": [
            "TATA POWER",
            "TATA POWER ELECTRICITY",
            "TATA POWER CO LTD",
        ],
    },
    {
        "canonical_name": "Airtel",
        "category": "Utilities",
        "subcategory": "Broadband & Mobile",
        "aliases": [
            "AIRTEL",
            "AIRTEL FIBER",
            "AIRTEL BROADBAND",
            "BHARTI AIRTEL",
            "AIRTEL PREPAID",
            "AIRTEL POSTPAID",
        ],
    },
    {
        "canonical_name": "Amazon",
        "category": "Shopping",
        "subcategory": "General Retail",
        "aliases": [
            "AMAZON",
            "AMAZON RETAIL INDIA",
            "AMAZON PAY INDIA",
            "AMZN MKTP",
            "AMAZON INDIA",
        ],
    },
    {
        "canonical_name": "Flipkart",
        "category": "Shopping",
        "subcategory": "General Retail",
        "aliases": [
            "FLIPKART",
            "FLIPKART INDIA PVT",
            "FLIPKART INTERNET",
        ],
    },
    {
        "canonical_name": "Starbucks",
        "category": "Food & Dining",
        "subcategory": "Restaurants & Cafes",
        "aliases": [
            "STARBUCKS",
            "STARBUCKS COFFEE",
            "TATA STARBUCKS",
        ],
    },
    {
        "canonical_name": "Google",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Software & Cloud Storage",
        "aliases": [
            "GOOGLE STORAGE",
            "GOOGLE ONE",
            "GOOGLE PLAY",
            "GOOGLE CLOUD",
        ],
    },
    {
        "canonical_name": "Microsoft",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Software & Cloud Storage",
        "aliases": [
            "MICROSOFT 365",
            "MSFT *SUBSCRIPTION",
            "MICROSOFT INDIA",
        ],
    },
    {
        "canonical_name": "GitHub",
        "category": "Entertainment & Subscriptions",
        "subcategory": "Software & Cloud Storage",
        "aliases": [
            "GITHUB COPILOT",
            "GITHUB INC",
            "GITHUB",
        ],
    },
    {
        "canonical_name": "Zerodha",
        "category": "Investments",
        "subcategory": "Stocks & Equities",
        "aliases": [
            "ZERODHA BROKING",
            "ZERODHA",
            "ZERODHA FUNDS",
        ],
    },
    {
        "canonical_name": "Apollo Pharmacy",
        "category": "Healthcare",
        "subcategory": "Pharmacy & Medicines",
        "aliases": [
            "APOLLO PHARMACY",
            "APOLLO HOSPITALS",
            "APOLLO 247",
        ],
    },
]

