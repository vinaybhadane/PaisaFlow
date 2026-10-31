"""Gemini AI Subscription Intelligence Engine.

Uses Gemini 3.5 Flash Lite to identify recurring subscriptions, utilities,
EMIs, and memberships from transaction descriptions, and deterministically
predicts the next expected billing date based on debited price, date, and cadence.
Includes full deterministic fallback matching for resilience.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid
from dateutil.relativedelta import relativedelta
import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.models.recurring_commitment import (
    RecurringCommitment,
    RecurringObservation,
)
from backend.app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Fallback pattern catalogue for popular Indian & Global subscriptions
KNOWN_SUBSCRIPTION_PATTERNS = [
    {
        "pattern": r"(?i)\b(netflix)\b",
        "name": "Netflix",
        "category": "Subscriptions & Streaming",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(spotify)\b",
        "name": "Spotify Premium",
        "category": "Subscriptions & Streaming",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(hotstar|disney\+?)\b",
        "name": "Disney+ Hotstar",
        "category": "Subscriptions & Streaming",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(youtube\s*(?:prem|premium))\b",
        "name": "YouTube Premium",
        "category": "Subscriptions & Streaming",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(amazon\s*prime|prime\s*video)\b",
        "name": "Amazon Prime",
        "category": "Subscriptions & Streaming",
        "default_cadence": "yearly",
    },
    {
        "pattern": r"(?i)\b(airtel\s*(?:fiber|broadband|bill|postpaid))\b",
        "name": "Airtel Broadband",
        "category": "Bills & Utilities",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(jio\s*(?:fiber|broadband|postpaid))\b",
        "name": "JioFiber",
        "category": "Bills & Utilities",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(act\s*fiber|act\s*corp)\b",
        "name": "ACT Fibernet",
        "category": "Bills & Utilities",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(chatgpt|openai)\b",
        "name": "OpenAI ChatGPT Plus",
        "category": "Software & AI",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(claude|anthropic)\b",
        "name": "Claude.ai Pro",
        "category": "Software & AI",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(google\s*one|google\s*storage)\b",
        "name": "Google One",
        "category": "Software & AI",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(apple\.com|apple\s*services|icloud)\b",
        "name": "Apple Services / iCloud",
        "category": "Subscriptions & Streaming",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(swiggy\s*one)\b",
        "name": "Swiggy One",
        "category": "Lifestyle & Food",
        "default_cadence": "quarterly",
    },
    {
        "pattern": r"(?i)\b(zomato\s*gold)\b",
        "name": "Zomato Gold",
        "category": "Lifestyle & Food",
        "default_cadence": "quarterly",
    },
    {
        "pattern": r"(?i)\b(cult\.?fit|curefit|gym)\b",
        "name": "Cult.fit Fitness",
        "category": "Health & Fitness",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(emi|loan|home\s*loan|car\s*loan|bajaj\s*fin)\b",
        "name": "Monthly EMI Obligation",
        "category": "Loans & EMIs",
        "default_cadence": "monthly",
    },
    {
        "pattern": r"(?i)\b(insurance|lic|hdfc\s*life|icici\s*pru|max\s*life|star\s*health)\b",
        "name": "Insurance Premium",
        "category": "Insurance",
        "default_cadence": "monthly",
    },
]


class GeminiSubscriptionService:
    """Detects recurring subscriptions with Gemini AI & predicts next billing dates."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.api_key = self.settings.GEMINI_API_KEY
        self.model_name = self.settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self._is_configured = bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key != "your_gemini_api_key_here"
        )
        if self._is_configured:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not configure Gemini SDK for subscriptions: {e}")
                self._is_configured = False

    @staticmethod
    def calculate_next_expected_date(debited_date: date, cadence: str) -> date:
        """Predict the next billing date based on debited date and cadence interval."""
        today = date.today()
        cadence_lower = (cadence or "monthly").lower().strip()

        if cadence_lower == "yearly":
            delta = relativedelta(years=1)
        elif cadence_lower == "half_yearly":
            delta = relativedelta(months=6)
        elif cadence_lower == "quarterly":
            delta = relativedelta(months=3)
        elif cadence_lower == "weekly":
            delta = timedelta(days=7)
        elif cadence_lower == "fortnightly":
            delta = timedelta(days=14)
        else:  # default monthly
            delta = relativedelta(months=1)

        next_d = debited_date + delta
        # If the next date has already passed relative to today, project to the next upcoming occurrence
        while next_d <= today:
            next_d += delta

        return next_d

    def _fallback_identify_subscription(
        self, original_desc: str, amount: Decimal
    ) -> Optional[Dict[str, Any]]:
        """Deterministic pattern matching for subscriptions when AI is unavailable."""
        text = original_desc.strip()
        for item in KNOWN_SUBSCRIPTION_PATTERNS:
            if re.search(item["pattern"], text):
                cadence = item["default_cadence"]
                # Infer yearly if keyword or amount indicates annual tier
                if re.search(r"(?i)\b(annual|yearly|12\s*m|yr)\b", text):
                    cadence = "yearly"
                elif item["name"] == "Amazon Prime" and amount > Decimal("999"):
                    cadence = "yearly"

                return {
                    "is_subscription": True,
                    "subscription_name": item["name"],
                    "category": item["category"],
                    "cadence": cadence,
                    "confidence": "high",
                    "reasoning": f"Identified via pattern rule for {item['name']}.",
                }

        # Generic recurring keyword checks
        if re.search(r"(?i)\b(subscription|sub|membership|recurring|autopay|mandate|standing\s*order)\b", text):
            return {
                "is_subscription": True,
                "subscription_name": text[:35],
                "category": "Subscriptions & Bills",
                "cadence": "monthly",
                "confidence": "medium",
                "reasoning": "Recurring subscription keywords detected in statement descriptor.",
            }

        return None

    async def analyze_transactions_for_subscriptions(
        self, transactions: List[Transaction]
    ) -> List[Dict[str, Any]]:
        """Analyze a list of transactions using Gemini or deterministic fallback.

        Returns a list of dicts with:
        - transaction: Transaction object
        - is_subscription: bool
        - subscription_name: str
        - cadence: str
        - category: str
        - predicted_next_date: date
        - confidence: str
        """
        results: List[Dict[str, Any]] = []
        if not transactions:
            return results

        # Filter candidates: debits/expenses only, skip own transfers and refunds
        eligible_txs = [
            tx
            for tx in transactions
            if tx.direction == "debit"
            and tx.transaction_type not in ("transfer", "refund")
            and not tx.is_excluded
        ]

        if not eligible_txs:
            return results

        # Prepare summary payload for batch AI evaluation
        batch_payload = [
            {
                "id": str(tx.id),
                "date": str(tx.transaction_date),
                "description": tx.original_description,
                "amount": float(tx.amount),
                "merchant": tx.normalized_description or "",
            }
            for tx in eligible_txs
        ]

        ai_detections: Dict[str, Dict[str, Any]] = {}

        if self._is_configured:
            try:
                prompt = (
                    "You are PaisaFlow's AI Subscription & Recurring Billing Intelligence Engine.\n"
                    "Analyze the following list of bank/card transaction descriptors. Identify which ones are "
                    "recurring subscriptions, streaming services, memberships, software licenses, broadband/mobile bills, "
                    "insurance premiums, or EMIs.\n\n"
                    "For EACH transaction that is a subscription or recurring bill, return a JSON object in a list.\n"
                    "Each item must have:\n"
                    "- id: string (matching transaction id)\n"
                    "- is_subscription: boolean (true)\n"
                    "- subscription_name: clean friendly name (e.g. 'Netflix', 'Spotify Premium', 'Airtel Broadband', 'Amazon Prime', 'OpenAI ChatGPT')\n"
                    "- cadence: 'monthly' | 'yearly' | 'quarterly' | 'weekly' (predict based on service and amount)\n"
                    "- category: 'Subscriptions & Streaming' | 'Bills & Utilities' | 'Software & AI' | 'Loans & EMIs' | 'Health & Fitness'\n"
                    "- confidence: 'high' | 'medium'\n"
                    "- reasoning: brief justification\n\n"
                    "Transactions:\n"
                    f"{json.dumps(batch_payload, indent=2)}\n\n"
                    "Return ONLY valid JSON matching this schema: [ { ... } ] with no markdown commentary."
                )

                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={"temperature": 0.1, "max_output_tokens": 1500},
                )
                response = await model.generate_content_async(prompt)
                resp_text = response.text.strip()
                # Clean markdown backticks if present
                if resp_text.startswith("```"):
                    resp_text = re.sub(r"^```(?:json)?\n", "", resp_text)
                    resp_text = re.sub(r"\n```$", "", resp_text).strip()

                parsed_items = json.loads(resp_text)
                if isinstance(parsed_items, list):
                    for item in parsed_items:
                        if isinstance(item, dict) and item.get("is_subscription"):
                            tx_id = str(item.get("id"))
                            ai_detections[tx_id] = item
            except Exception as e:
                logger.warning(f"Gemini subscription identification failed, falling back to rule engine: {e}")

        # Assemble results for each eligible transaction
        for tx in eligible_txs:
            tx_id_str = str(tx.id)
            detection = ai_detections.get(tx_id_str)

            if not detection:
                # Deterministic pattern matching fallback
                detection = self._fallback_identify_subscription(
                    tx.original_description, tx.amount
                )

            if detection and detection.get("is_subscription"):
                cadence = detection.get("cadence") or "monthly"
                pred_date = self.calculate_next_expected_date(tx.transaction_date, cadence)
                results.append(
                    {
                        "transaction": tx,
                        "is_subscription": True,
                        "subscription_name": detection.get("subscription_name") or tx.original_description[:30],
                        "cadence": cadence,
                        "category": detection.get("category") or "Subscriptions & Streaming",
                        "predicted_next_date": pred_date,
                        "confidence": detection.get("confidence") or "high",
                        "reasoning": detection.get("reasoning") or "Grounded from statement descriptor.",
                        "is_gemini_derived": tx_id_str in ai_detections,
                    }
                )

        return results

    async def process_and_persist_subscriptions(
        self, db: AsyncSession, user_id: uuid.UUID, transactions: List[Transaction]
    ) -> List[RecurringCommitment]:
        """Identify subscriptions from transactions, predict next dates, and persist to database.

        Idempotent: updates existing commitments or creates new ones.
        """
        detections = await self.analyze_transactions_for_subscriptions(transactions)
        if not detections:
            return []

        persisted: List[RecurringCommitment] = []

        for det in detections:
            tx: Transaction = det["transaction"]
            sub_name: str = det["subscription_name"]
            cadence: str = det["cadence"]
            next_date: date = det["predicted_next_date"]
            conf: str = det["confidence"]

            # Check if matching commitment already exists for this user
            existing_stmt = select(RecurringCommitment).where(
                RecurringCommitment.user_id == user_id,
                RecurringCommitment.display_name == sub_name,
            )
            res = await db.execute(existing_stmt)
            existing = res.scalar_one_or_none()

            estimated_days = 30
            if cadence == "yearly":
                estimated_days = 365
            elif cadence == "quarterly":
                estimated_days = 90
            elif cadence == "weekly":
                estimated_days = 7

            evidence_dict = {
                "source": "gemini_subscription_intelligence" if det.get("is_gemini_derived") else "deterministic_subscription_detector",
                "original_description": tx.original_description,
                "debited_amount": str(tx.amount),
                "debited_date": str(tx.transaction_date),
                "predicted_next_date": str(next_date),
                "cadence": cadence,
                "reasoning": det.get("reasoning", ""),
            }

            if existing:
                commitment = existing
                # Update latest observation and forward predicted date
                if not commitment.last_observed_date or tx.transaction_date >= commitment.last_observed_date:
                    commitment.last_observed_date = tx.transaction_date
                    commitment.next_expected_date = next_date
                    commitment.typical_amount = tx.amount
                commitment.evidence = evidence_dict
            else:
                commitment = RecurringCommitment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    merchant_id=tx.merchant_id,
                    display_name=sub_name,
                    cadence=cadence,
                    estimated_cadence_days=estimated_days,
                    typical_amount=tx.amount,
                    min_amount=tx.amount,
                    max_amount=tx.amount,
                    currency=tx.currency,
                    confidence=conf,
                    status="likely",
                    last_observed_date=tx.transaction_date,
                    next_expected_date=next_date,
                    evidence=evidence_dict,
                )
                db.add(commitment)
                await db.flush()

            # Record observation linking to this transaction
            obs_stmt = select(RecurringObservation).where(
                RecurringObservation.commitment_id == commitment.id,
                RecurringObservation.transaction_id == tx.id,
            )
            obs_res = await db.execute(obs_stmt)
            if not obs_res.scalar_one_or_none():
                obs = RecurringObservation(
                    id=uuid.uuid4(),
                    commitment_id=commitment.id,
                    transaction_id=tx.id,
                    observed_amount=tx.amount,
                    observed_date=tx.transaction_date,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(obs)

            persisted.append(commitment)

        await db.commit()
        return persisted
