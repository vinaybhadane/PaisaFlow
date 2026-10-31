"""Synthetic Demo Data Pipeline Service.

Generates realistic but entirely fictional financial records for demo personas:
1. Asha Mehta — Salaried Professional
2. Kabir Shah — Freelance Consultant

Strict adherence to docs/12_SYNTHETIC_DATA_SPEC.md:
- Deterministic, fixed random seeds.
- Includes merchant aliases, price changes, refunds, own-account transfers, and duplicates.
- Idempotent and safely resettable.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import random
from typing import Any, Dict
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.account import Account
from backend.app.models.category import Category
from backend.app.models.demo_profile import DemoProfile
from backend.app.models.financial_fact import FinancialFact
from backend.app.models.goal import Goal
from backend.app.models.merchant import Merchant, MerchantAlias
from backend.app.models.recurring_commitment import (
    PriceChangeEvent,
    RecurringCommitment,
    RecurringObservation,
)
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


class DemoDataService:
    """Service for deterministic generation and safe reset of synthetic demo data."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_fingerprint(self, account_id: uuid.UUID, trans_date: date, amount: Decimal, desc: str) -> str:
        """Create deterministic duplicate fingerprint."""
        raw = f"{account_id}:{trans_date.isoformat()}:{str(amount)}:{desc.strip().upper()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    async def get_or_create_system_categories(self, session: AsyncSession) -> Dict[str, Category]:
        """Seed canonical taxonomy if not already present."""
        category_specs = [
            ("Income", "income", 10),
            ("Salary", "income", 11),
            ("Freelance & Invoicing", "income", 12),
            ("Refunds", "income", 13),
            ("Housing", "expense", 20),
            ("Utilities", "expense", 30),
            ("Food & Dining", "expense", 40),
            ("Groceries", "expense", 41),
            ("Dining Out", "expense", 42),
            ("Transportation", "expense", 50),
            ("Subscriptions & Entertainment", "expense", 60),
            ("Shopping", "expense", 70),
            ("Health & Medical", "expense", 80),
            ("Transfers", "transfer", 90),
        ]

        categories: Dict[str, Category] = {}
        for name, cat_type, sort_order in category_specs:
            stmt = select(Category).where(Category.name == name)
            res = await session.execute(stmt)
            cat = res.scalar_one_or_none()
            if not cat:
                cat = Category(
                    id=uuid.uuid4(),
                    name=name,
                    category_type=cat_type,
                    is_system=True,
                    sort_order=sort_order,
                )
                session.add(cat)
                await session.flush()
            categories[name] = cat

        return categories

    async def get_or_create_merchants(
        self, session: AsyncSession, categories: Dict[str, Category]
    ) -> Dict[str, Merchant]:
        """Seed fictional merchants and aliases."""
        merchant_specs = [
            ("METRO HOME RENT", categories["Housing"].id, ["MHR RENT", "METRO PROPERTIES POS"]),
            ("NORTHSTAR UTILITIES", categories["Utilities"].id, ["NSTAR ELEC", "NORTHSTAR POWER BILL"]),
            ("STREAMBOX MEDIA", categories["Subscriptions & Entertainment"].id, ["STREAMBOX SUB", "STREAMBOX DIGITAL"]),
            ("FRESHMART RETAIL", categories["Groceries"].id, ["FRESH MART POS", "FRESHMART HYPER"]),
            ("CITYRIDE MOBILITY", categories["Transportation"].id, ["CITYRIDE APP", "CR*MOBILITY"]),
            ("CLOUDNEST STORAGE", categories["Subscriptions & Entertainment"].id, ["CLDNEST BILL", "CLOUDNEST CLOUD"]),
        ]

        merchants: Dict[str, Merchant] = {}
        for canonical_name, cat_id, aliases in merchant_specs:
            stmt = select(Merchant).where(Merchant.canonical_name == canonical_name)
            res = await session.execute(stmt)
            merchant = res.scalar_one_or_none()
            if not merchant:
                merchant = Merchant(
                    id=uuid.uuid4(),
                    canonical_name=canonical_name,
                    category_id=cat_id,
                    description=f"Fictional synthetic merchant {canonical_name}",
                    is_fictional_demo=True,
                )
                session.add(merchant)
                await session.flush()

                for alias in aliases:
                    alias_record = MerchantAlias(
                        id=uuid.uuid4(),
                        merchant_id=merchant.id,
                        alias_pattern=alias,
                        match_type="exact",
                        priority=100,
                        is_active=True,
                    )
                    session.add(alias_record)
                await session.flush()

            merchants[canonical_name] = merchant

        return merchants

    async def seed_asha_mehta(
        self,
        session: AsyncSession,
        categories: Dict[str, Category],
        merchants: Dict[str, Merchant],
    ) -> User:
        """Seed Persona 1: Asha Mehta (Salaried Professional)."""
        email = "asha.mehta.demo@paisaflow.synthetic"
        user_stmt = select(User).where(User.email == email)
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        if user:
            logger.info("Persona Asha Mehta already seeded. Skipping to preserve idempotency.")
            return user

        user = User(
            id=uuid.uuid4(),
            display_name="Asha Mehta (Demo)",
            email=email,
            locale="en-IN",
            timezone="Asia/Kolkata",
            default_currency="INR",
        )
        session.add(user)
        await session.flush()

        profile = DemoProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            persona_key="asha_mehta",
            is_synthetic=True,
            profile_label="Asha Mehta — Salaried Professional",
        )
        session.add(profile)
        await session.flush()

        checking_acct = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            demo_profile_id=profile.id,
            display_name="Salary Checking Account",
            account_type="checking",
            currency="INR",
            is_synthetic=True,
        )
        savings_acct = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            demo_profile_id=profile.id,
            display_name="High-Yield Savings Account",
            account_type="savings",
            currency="INR",
            is_synthetic=True,
        )
        session.add_all([checking_acct, savings_acct])
        await session.flush()

        # Seed 6 months of historical transactions (May to October 2026)
        base_date = date(2026, 5, 1)
        months_count = 6

        # Recurring commitment: Streambox Media (Price change from ₹149 to ₹179 in month 4)
        streambox_rc = RecurringCommitment(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_id=merchants["STREAMBOX MEDIA"].id,
            display_name="Streambox Media Subscription",
            cadence="monthly",
            estimated_cadence_days=30,
            typical_amount=Decimal("179.00"),
            min_amount=Decimal("149.00"),
            max_amount=Decimal("179.00"),
            currency="INR",
            confidence="high",
            status="confirmed",
            last_observed_date=date(2026, 10, 15),
            next_expected_date=date(2026, 11, 15),
            evidence={"observations": 6, "cadence_regularity": 0.98},
        )
        session.add(streambox_rc)
        await session.flush()

        # Price change event for Streambox Media
        price_event = PriceChangeEvent(
            id=uuid.uuid4(),
            commitment_id=streambox_rc.id,
            previous_amount=Decimal("149.00"),
            new_amount=Decimal("179.00"),
            absolute_change=Decimal("30.00"),
            percentage_change=Decimal("20.13"),
            detected_at=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
            evidence={"prior_payments": 3, "new_payments": 3},
            status="confirmed_by_user",
        )
        session.add(price_event)

        # Generate Monthly Cycles
        for m in range(months_count):
            month_date = base_date + timedelta(days=m * 30)

            # 1. Salary (with slight date jitter around 28th-1st)
            jitter_day = self.rng.randint(-1, 1)
            salary_date = month_date.replace(day=28) + timedelta(days=jitter_day)
            salary_tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=checking_acct.id,
                transaction_date=salary_date,
                original_description="NEFT CR ACME CORP SALARY",
                normalized_description="Acme Corp Salary",
                amount=Decimal("48000.00"),
                currency="INR",
                direction="credit",
                transaction_type="income",
                category_id=categories["Salary"].id,
                categorization_method="rule_match",
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    checking_acct.id, salary_date, Decimal("48000.00"), "ACME SALARY"
                ),
            )
            session.add(salary_tx)

            # 2. Rent (Metro Home Rent ₹15,000 on 5th)
            rent_date = month_date.replace(day=5)
            rent_tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=checking_acct.id,
                transaction_date=rent_date,
                original_description="UPI/MHR RENT/METRO PROPERTIES",
                normalized_description="Metro Home Rent",
                merchant_id=merchants["METRO HOME RENT"].id,
                amount=Decimal("15000.00"),
                currency="INR",
                direction="debit",
                transaction_type="expense",
                category_id=categories["Housing"].id,
                categorization_method="alias_match",
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    checking_acct.id, rent_date, Decimal("15000.00"), "MHR RENT"
                ),
            )
            session.add(rent_tx)

            # 3. Utilities (Northstar variable bill ₹1,800 to ₹2,400)
            util_date = month_date.replace(day=10)
            util_amt = Decimal(str(self.rng.randint(1800, 2400))) + Decimal("0.50")
            util_tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=checking_acct.id,
                transaction_date=util_date,
                original_description="NSTAR ELEC BILL PAYMENT",
                normalized_description="Northstar Utilities",
                merchant_id=merchants["NORTHSTAR UTILITIES"].id,
                amount=util_amt,
                currency="INR",
                direction="debit",
                transaction_type="expense",
                category_id=categories["Utilities"].id,
                categorization_method="alias_match",
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    checking_acct.id, util_date, util_amt, "NSTAR ELEC"
                ),
            )
            session.add(util_tx)

            # 4. Streambox Subscription (₹149 for first 3 months, ₹179 for remaining)
            sub_date = month_date.replace(day=15)
            sub_amt = Decimal("149.00") if m < 3 else Decimal("179.00")
            sub_tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=checking_acct.id,
                transaction_date=sub_date,
                original_description="STREAMBOX SUB AUTOPAY",
                normalized_description="Streambox Media",
                merchant_id=merchants["STREAMBOX MEDIA"].id,
                amount=sub_amt,
                currency="INR",
                direction="debit",
                transaction_type="expense",
                category_id=categories["Subscriptions & Entertainment"].id,
                categorization_method="alias_match",
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    checking_acct.id, sub_date, sub_amt, "STREAMBOX SUB"
                ),
            )
            session.add(sub_tx)
            await session.flush()

            # Record observation for recurring commitment
            obs = RecurringObservation(
                id=uuid.uuid4(),
                commitment_id=streambox_rc.id,
                transaction_id=sub_tx.id,
                observed_amount=sub_amt,
                observed_date=sub_date,
            )
            session.add(obs)

            # 5. Groceries & Transport with Aliases
            for g_day in [8, 18, 26]:
                gro_date = month_date.replace(day=g_day)
                alias_desc = "FRESHMART HYPER" if g_day == 18 else "FRESH MART POS"
                gro_amt = Decimal(str(self.rng.randint(800, 2200))) + Decimal("0.00")
                gro_tx = Transaction(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    account_id=checking_acct.id,
                    transaction_date=gro_date,
                    original_description=alias_desc,
                    normalized_description="Freshmart Retail",
                    merchant_id=merchants["FRESHMART RETAIL"].id,
                    amount=gro_amt,
                    currency="INR",
                    direction="debit",
                    transaction_type="expense",
                    category_id=categories["Groceries"].id,
                    categorization_method="alias_match",
                    confidence="high",
                    review_status="confirmed",
                    duplicate_fingerprint=self.generate_fingerprint(
                        checking_acct.id, gro_date, gro_amt, alias_desc
                    ),
                )
                session.add(gro_tx)

        # Edge Case 1: Own-Account Transfer (₹5,000 checking -> savings, excluded from income/expense)
        transfer_date = date(2026, 9, 29)
        transfer_amt = Decimal("5000.00")
        tx_debit = Transaction(
            id=uuid.uuid4(),
            user_id=user.id,
            account_id=checking_acct.id,
            transaction_date=transfer_date,
            original_description="TRF TO HY-SAVINGS ACCT",
            normalized_description="Transfer to Savings",
            amount=transfer_amt,
            currency="INR",
            direction="debit",
            transaction_type="transfer",
            category_id=categories["Transfers"].id,
            categorization_method="system",
            confidence="high",
            review_status="confirmed",
            is_excluded=True,
            duplicate_fingerprint=self.generate_fingerprint(
                checking_acct.id, transfer_date, transfer_amt, "TRF SAVINGS"
            ),
        )
        tx_credit = Transaction(
            id=uuid.uuid4(),
            user_id=user.id,
            account_id=savings_acct.id,
            transaction_date=transfer_date,
            original_description="TRF FROM CHK ACCT",
            normalized_description="Transfer from Checking",
            amount=transfer_amt,
            currency="INR",
            direction="credit",
            transaction_type="transfer",
            category_id=categories["Transfers"].id,
            categorization_method="system",
            confidence="high",
            review_status="confirmed",
            is_excluded=True,
            duplicate_fingerprint=self.generate_fingerprint(
                savings_acct.id, transfer_date, transfer_amt, "TRF FROM CHK"
            ),
        )
        session.add_all([tx_debit, tx_credit])

        # Edge Case 2: Refund (₹850 shopping refund)
        refund_date = date(2026, 8, 22)
        refund_amt = Decimal("850.00")
        refund_tx = Transaction(
            id=uuid.uuid4(),
            user_id=user.id,
            account_id=checking_acct.id,
            transaction_date=refund_date,
            original_description="REFUND CLOTHING STORE",
            normalized_description="Clothing Store Refund",
            amount=refund_amt,
            currency="INR",
            direction="credit",
            transaction_type="refund",
            category_id=categories["Refunds"].id,
            categorization_method="keyword",
            confidence="high",
            review_status="confirmed",
            duplicate_fingerprint=self.generate_fingerprint(
                checking_acct.id, refund_date, refund_amt, "REFUND CLOTH"
            ),
        )
        session.add(refund_tx)

        # Edge Case 3: Duplicate transaction flagged
        dup_date = date(2026, 9, 12)
        dup_amt = Decimal("450.00")
        dup_fp = self.generate_fingerprint(checking_acct.id, dup_date, dup_amt, "CAFE COFFEE DAY")
        tx_dup1 = Transaction(
            id=uuid.uuid4(),
            user_id=user.id,
            account_id=checking_acct.id,
            transaction_date=dup_date,
            original_description="CAFE COFFEE DAY POS",
            normalized_description="Cafe Coffee Day",
            amount=dup_amt,
            currency="INR",
            direction="debit",
            transaction_type="expense",
            category_id=categories["Dining Out"].id,
            review_status="confirmed",
            duplicate_fingerprint=dup_fp,
        )
        tx_dup2 = Transaction(
            id=uuid.uuid4(),
            user_id=user.id,
            account_id=checking_acct.id,
            transaction_date=dup_date,
            original_description="CAFE COFFEE DAY POS",
            normalized_description="Cafe Coffee Day",
            amount=dup_amt,
            currency="INR",
            direction="debit",
            transaction_type="expense",
            category_id=categories["Dining Out"].id,
            review_status="flagged",
            duplicate_fingerprint=dup_fp,
        )
        session.add_all([tx_dup1, tx_dup2])

        # Seed Goal: Emergency Fund
        goal = Goal(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Emergency Fund",
            description="Safety net covering essential monthly expenses.",
            target_amount=Decimal("50000.00"),
            current_saved_amount=Decimal("21000.00"),
            currency="INR",
            target_date=date(2027, 4, 30),
            priority="high",
            contribution_frequency="monthly",
            planned_contribution=Decimal("5000.00"),
            status="active",
        )
        session.add(goal)

        # Seed Financial Facts (Living Money Model)
        fact_income = FinancialFact(
            id=uuid.uuid4(),
            user_id=user.id,
            fact_type="income",
            label="Monthly Base Salary",
            amount=Decimal("48000.00"),
            currency="INR",
            source_type="user_confirmed",
            effective_from=date(2026, 1, 1),
            confidence="high",
            source_reference={"verified_by": "user", "basis": "Acme Corp Employment"},
        )
        fact_rent = FinancialFact(
            id=uuid.uuid4(),
            user_id=user.id,
            fact_type="fixed_cost",
            label="Apartment Rent",
            amount=Decimal("15000.00"),
            currency="INR",
            source_type="user_confirmed",
            effective_from=date(2026, 1, 1),
            confidence="high",
            source_reference={"verified_by": "user", "lease_period": "2026"},
        )
        session.add_all([fact_income, fact_rent])

        await session.commit()
        logger.info("Successfully seeded Asha Mehta profile and transactions.")
        return user

    async def seed_kabir_shah(
        self,
        session: AsyncSession,
        categories: Dict[str, Category],
        merchants: Dict[str, Merchant],
    ) -> User:
        """Seed Persona 2: Kabir Shah (Freelancer Persona with Irregular Income)."""
        email = "kabir.shah.demo@paisaflow.synthetic"
        user_stmt = select(User).where(User.email == email)
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        if user:
            logger.info("Persona Kabir Shah already seeded. Skipping to preserve idempotency.")
            return user

        user = User(
            id=uuid.uuid4(),
            display_name="Kabir Shah (Demo)",
            email=email,
            locale="en-IN",
            timezone="Asia/Kolkata",
            default_currency="INR",
        )
        session.add(user)
        await session.flush()

        profile = DemoProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            persona_key="kabir_shah",
            is_synthetic=True,
            profile_label="Kabir Shah — Freelance Consultant",
        )
        session.add(profile)
        await session.flush()

        operating_acct = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            demo_profile_id=profile.id,
            display_name="Freelance Operating Account",
            account_type="checking",
            currency="INR",
            is_synthetic=True,
        )
        savings_acct = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            demo_profile_id=profile.id,
            display_name="Personal Savings Account",
            account_type="savings",
            currency="INR",
            is_synthetic=True,
        )
        session.add_all([operating_acct, savings_acct])
        await session.flush()

        # Seed irregular client receipts across 6 months
        receipt_specs = [
            (date(2026, 5, 12), Decimal("35000.00"), "CLIENT INVOICE #1014 - NEXUS LABS"),
            (date(2026, 6, 20), Decimal("55000.00"), "CLIENT PAYMENT - VERITAS TECH DESIGN"),
            (date(2026, 7, 10), Decimal("42000.00"), "INVOICE #1022 - ZEPHYR STUDIOS"),
            (date(2026, 8, 28), Decimal("60000.00"), "CLIENT RETAINER - APEX APPS"),
            (date(2026, 9, 14), Decimal("38000.00"), "CLIENT INVOICE #1031 - NEXUS LABS"),
            (date(2026, 10, 25), Decimal("52000.00"), "PROJECT MILESTONE - ORBIT CONSULTING"),
        ]

        for r_date, r_amt, r_desc in receipt_specs:
            tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=operating_acct.id,
                transaction_date=r_date,
                original_description=r_desc,
                normalized_description="Client Invoice Receipt",
                amount=r_amt,
                currency="INR",
                direction="credit",
                transaction_type="income",
                category_id=categories["Freelance & Invoicing"].id,
                categorization_method="client_match",
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(operating_acct.id, r_date, r_amt, r_desc),
            )
            session.add(tx)

        # Monthly Studio Rent (₹12,000)
        for m in range(6):
            r_date = date(2026, 5, 7) + timedelta(days=m * 30)
            tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=operating_acct.id,
                transaction_date=r_date,
                original_description="STUDIO RENT PAYMENT",
                normalized_description="Studio Space Rent",
                amount=Decimal("12000.00"),
                currency="INR",
                direction="debit",
                transaction_type="expense",
                category_id=categories["Housing"].id,
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    operating_acct.id, r_date, Decimal("12000.00"), "STUDIO RENT"
                ),
            )
            session.add(tx)

        # Cloudnest Storage Subscription (₹799/month)
        cloudnest_rc = RecurringCommitment(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_id=merchants["CLOUDNEST STORAGE"].id,
            display_name="Cloudnest Cloud Storage",
            cadence="monthly",
            typical_amount=Decimal("799.00"),
            currency="INR",
            confidence="high",
            status="confirmed",
            last_observed_date=date(2026, 10, 18),
            next_expected_date=date(2026, 11, 18),
        )
        session.add(cloudnest_rc)

        for m in range(6):
            c_date = date(2026, 5, 18) + timedelta(days=m * 30)
            tx = Transaction(
                id=uuid.uuid4(),
                user_id=user.id,
                account_id=operating_acct.id,
                transaction_date=c_date,
                original_description="CLDNEST BILL PAYMENT",
                normalized_description="Cloudnest Storage",
                merchant_id=merchants["CLOUDNEST STORAGE"].id,
                amount=Decimal("799.00"),
                currency="INR",
                direction="debit",
                transaction_type="expense",
                category_id=categories["Subscriptions & Entertainment"].id,
                confidence="high",
                review_status="confirmed",
                duplicate_fingerprint=self.generate_fingerprint(
                    operating_acct.id, c_date, Decimal("799.00"), "CLDNEST BILL"
                ),
            )
            session.add(tx)

        # Seed Goal: New MacBook Pro Workstation
        goal = Goal(
            id=uuid.uuid4(),
            user_id=user.id,
            title="MacBook Pro Workstation",
            description="Upgraded hardware for client video editing and dev work.",
            target_amount=Decimal("120000.00"),
            current_saved_amount=Decimal("45000.00"),
            currency="INR",
            target_date=date(2027, 7, 31),
            priority="medium",
            contribution_frequency="monthly",
            planned_contribution=Decimal("8500.00"),
            status="active",
        )
        session.add(goal)

        await session.commit()
        logger.info("Successfully seeded Kabir Shah profile and transactions.")
        return user

    async def seed_all(self, session: AsyncSession) -> Dict[str, Any]:
        """Seed all system categories, merchants, and both personas."""
        categories = await self.get_or_create_system_categories(session)
        merchants = await self.get_or_create_merchants(session, categories)
        asha = await self.seed_asha_mehta(session, categories, merchants)
        kabir = await self.seed_kabir_shah(session, categories, merchants)

        return {
            "categories_count": len(categories),
            "merchants_count": len(merchants),
            "personas_seeded": [asha.display_name, kabir.display_name],
        }

    async def reset_synthetic_demo_data(self, session: AsyncSession) -> Dict[str, int]:
        """Safely delete ONLY synthetic demo records. Never deletes real or production records."""
        # Find all synthetic demo profile IDs
        stmt = select(DemoProfile.user_id).where(DemoProfile.is_synthetic == True)  # noqa: E712
        synthetic_user_ids = (await session.execute(stmt)).scalars().all()

        if not synthetic_user_ids:
            logger.info("No synthetic demo profiles found to reset.")
            return {"deleted_users": 0}

        # Cascade deletes will clean up related demo_profiles, accounts, transactions, goals, facts
        del_stmt = delete(User).where(User.id.in_(synthetic_user_ids))
        result = await session.execute(del_stmt)
        await session.commit()

        deleted_count = result.rowcount or len(synthetic_user_ids)
        logger.info(f"Safely reset {deleted_count} synthetic demo users and their dependent records.")
        return {"deleted_users": deleted_count}
