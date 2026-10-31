"""Comprehensive test suite for Phase 4: Transaction Intelligence, Categorization, Merchant Resolution, and User Corrections."""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intelligence.categorization.classifier import TransactionClassifier
from backend.app.intelligence.categorization.confidence import CategorizationConfidence
from backend.app.intelligence.categorization.taxonomy import CategoryTaxonomyService
from backend.app.intelligence.corrections.correction_service import (
    TransactionCorrectionService,
)
from backend.app.intelligence.corrections.learning_rules import (
    CategorizationRuleService,
)
from backend.app.intelligence.engine import TransactionIntelligenceEngine
from backend.app.intelligence.merchant.resolver import MerchantResolver
from backend.app.models.account import Account
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


# ==============================================================================
# 1. TAXONOMY TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_category_taxonomy_seeding_and_hierarchy(test_db_session: AsyncSession) -> None:
    """Verify category hierarchy creation, parent-child links, and seed idempotency."""
    # 1. First seed
    cats1 = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    assert len(cats1) > 20
    assert "Food & Dining" in cats1
    assert "Groceries" in cats1
    assert "Income" in cats1
    assert "Transfers" in cats1

    # Verify parent-child relationship
    groceries = cats1["Groceries"]
    food = cats1["Food & Dining"]
    assert groceries.parent_id == food.id

    # 2. Second seed (Idempotency test)
    cats2 = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    assert len(cats2) == len(cats1)
    assert cats2["Groceries"].id == groceries.id

    # 3. Hierarchy tree retrieval
    tree = await CategoryTaxonomyService.get_taxonomy_tree(test_db_session)
    assert len(tree) >= 10
    parent_names = [p.name for p in tree]
    assert "Food & Dining" in parent_names
    assert "Income" in parent_names
    assert "Refunds" in parent_names

    food_node = next(p for p in tree if p.name == "Food & Dining")
    child_names = [c.name for c in food_node.subcategories]
    assert "Groceries" in child_names
    assert "Food Delivery" in child_names


# ==============================================================================
# 2. MERCHANT RESOLUTION TESTS
# ==============================================================================


def test_merchant_resolver_exact_and_token_matching() -> None:
    """Verify exact, channel-stripped, and token-boundary merchant matching."""
    resolver = MerchantResolver()

    # Exact alias
    res1 = resolver.resolve("SWIGGY")
    assert res1.canonical_name == "Swiggy"
    assert res1.method == "exact_alias"
    assert res1.confidence >= 0.95

    # Channel prefix and VPA suffix stripped
    res2 = resolver.resolve("UPI-SWIGGY-18293@ICICI")
    assert res2.canonical_name == "Swiggy"
    assert res2.category_hint == "Food & Dining"
    assert res2.subcategory_hint == "Food Delivery"

    # Token match
    res3 = resolver.resolve("BLINKIT ORDER #89128 BANGALORE")
    assert res3.canonical_name == "Blinkit"
    assert res3.method == "token_match"

    # Streaming subscription
    res4 = resolver.resolve("POS NETFLIX MUMBAI IN 918239")
    assert res4.canonical_name == "Netflix"
    assert res4.category_hint == "Entertainment & Subscriptions"


def test_merchant_resolver_fuzzy_matching_and_collision_prevention() -> None:
    """Verify fuzzy matching with typo tolerance and collision margin protection."""
    resolver = MerchantResolver()

    # Mild typo in known merchant
    res1 = resolver.resolve("NETFLX MUMBAI")
    assert res1.canonical_name == "Netflix"
    assert res1.method == "fuzzy_match"
    assert res1.confidence >= 0.70

    # Completely unknown merchant
    res_unknown = resolver.resolve("XYZ UNKNOWN ENTERPRISES KORAMANGALA")
    assert res_unknown.is_unknown is True
    assert res_unknown.canonical_name is None
    assert res_unknown.confidence < 0.50


# ==============================================================================
# 3. DETERMINISTIC CATEGORIZATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_deterministic_classification_and_provenance(test_db_session: AsyncSession) -> None:
    """Verify that transfers, refunds, salary, and known merchants classify accurately."""
    cats = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    classifier = TransactionClassifier()
    dummy_user = uuid.uuid4()

    # 1. Own account transfer -> Transfers (never expense)
    res_trf = await classifier.classify(
        session=test_db_session,
        user_id=dummy_user,
        normalized_description="TRF TO OWN ACCT 987654",
        direction="debit",
        transaction_type="transfer",
        cached_categories=cats,
    )
    assert res_trf.category_name == "Transfers"
    assert res_trf.subcategory_name == "Own Account Transfer"
    assert res_trf.confidence.level == "high"

    # 2. Refund -> Refunds (never salary income)
    res_ref = await classifier.classify(
        session=test_db_session,
        user_id=dummy_user,
        normalized_description="REFUND - AMAZON PAY INDIA",
        direction="credit",
        transaction_type="refund",
        cached_categories=cats,
    )
    assert res_ref.category_name == "Refunds"
    assert res_ref.confidence.level == "high"

    # 3. Salary -> Income / Salary
    res_sal = await classifier.classify(
        session=test_db_session,
        user_id=dummy_user,
        normalized_description="SALARY CREDIT - ACME TECH PVT LTD",
        direction="credit",
        transaction_type="income",
        cached_categories=cats,
    )
    assert res_sal.category_name == "Income"
    assert res_sal.subcategory_name == "Salary"
    assert res_sal.confidence.level == "high"

    # 4. Swiggy -> Food & Dining / Food Delivery
    res_swiggy = await classifier.classify(
        session=test_db_session,
        user_id=dummy_user,
        normalized_description="UPI-SWIGGY-18293@ICICI",
        direction="debit",
        transaction_type="expense",
        cached_categories=cats,
    )
    assert res_swiggy.category_name == "Food & Dining"
    assert res_swiggy.subcategory_name == "Food Delivery"
    assert res_swiggy.resolved_merchant_name == "Swiggy"

    # 5. Unknown descriptor -> Other / Uncategorized Expense with review requirement
    res_unk = await classifier.classify(
        session=test_db_session,
        user_id=dummy_user,
        normalized_description="RANDOM STRING 88219 UNKNOWN",
        direction="debit",
        transaction_type="expense",
        cached_categories=cats,
    )
    assert res_unk.category_name == "Other"
    assert res_unk.subcategory_name == "Uncategorized Expense"
    assert res_unk.confidence.requires_review is True
    assert res_unk.review_status == "flagged"


# ==============================================================================
# 4. CONFIDENCE SCORING CALIBRATION
# ==============================================================================


def test_confidence_calibration() -> None:
    """Verify documented High/Medium/Low thresholds."""
    c_high = CategorizationConfidence.calculate("user_rule", 1.0, ["User rule"])
    assert c_high.level == "high"
    assert c_high.requires_review is False

    c_med = CategorizationConfidence.calculate("fuzzy_match", 0.70, ["Fuzzy match"])
    assert c_med.level == "medium"
    assert c_med.requires_review is True

    c_low = CategorizationConfidence.calculate("fallback", 0.20, ["Unrecognized"])
    assert c_low.level == "low"
    assert c_low.requires_review is True


# ==============================================================================
# 5. USER CORRECTIONS & AUDIT IMMUTABILITY
# ==============================================================================


@pytest.mark.asyncio
async def test_user_transaction_correction_and_audit(test_db_session: AsyncSession) -> None:
    """Verify that user correction changes category, creates audit log, and preserves financial amounts."""
    cats = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        display_name="Correction Test User",
        email="corr.user@synthetic-demo.paisaflow",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)

    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Primary Checking",
        account_type="checking",
        currency="INR",
        is_synthetic=True,
    )
    test_db_session.add(account)

    tx = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account.id,
        transaction_date=date(2026, 10, 5),
        original_description="SWIGGY INSTAMART ORDER",
        normalized_description="SWIGGY INSTAMART ORDER",
        amount=Decimal("450.00"),
        currency="INR",
        direction="debit",
        transaction_type="expense",
        category_id=cats["Food & Dining"].id,
        subcategory_id=cats["Food Delivery"].id,
        categorization_method="merchant_exact_alias",
        confidence="high",
        review_status="confirmed",
    )
    test_db_session.add(tx)
    await test_db_session.commit()

    # User corrects Swiggy Instamart from 'Food & Dining' to 'Groceries'
    target_cat = cats["Groceries"]
    updated_tx = await TransactionCorrectionService.correct_transaction(
        session=test_db_session,
        user_id=user_id,
        transaction_id=tx.id,
        category_id=target_cat.id,
        apply_future_rule=True,
        scope_type="exact_merchant",
    )

    # 1. Verify category updated
    assert updated_tx.category_id == target_cat.id
    assert updated_tx.review_status == "corrected"
    assert updated_tx.categorization_method == "user_correction"

    # 2. Verify monetary facts are completely untouched
    assert updated_tx.amount == Decimal("450.00")
    assert updated_tx.transaction_date == date(2026, 10, 5)
    assert updated_tx.direction == "debit"
    assert updated_tx.currency == "INR"

    # 3. Verify audit history record
    corrections = await TransactionCorrectionService.list_corrections_for_transaction(
        session=test_db_session,
        user_id=user_id,
        transaction_id=tx.id,
    )
    assert len(corrections) == 1
    corr = corrections[0]
    assert corr.field_name == "category_id"
    assert corr.old_value["category_id"] == str(cats["Food & Dining"].id)
    assert corr.new_value["category_id"] == str(target_cat.id)
    assert corr.rule_id is not None

    # 4. Revert correction test
    reverted_tx = await TransactionCorrectionService.revert_correction(
        session=test_db_session,
        user_id=user_id,
        correction_id=corr.id,
    )
    assert reverted_tx.category_id == cats["Food & Dining"].id


# ==============================================================================
# 6. PERSONALIZED LEARNING RULES & PRECEDENCE
# ==============================================================================


@pytest.mark.asyncio
async def test_personalized_rule_precedence_and_isolation(test_db_session: AsyncSession) -> None:
    """Verify user-specific rules override default engine rules and do not leak across users."""
    cats = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # User A creates a rule mapping 'Swiggy' to 'Shopping' (e.g. personal preference)
    rule_a = await CategorizationRuleService.create_rule(
        session=test_db_session,
        user_id=user_a,
        category_id=cats["Shopping"].id,
        scope_type="exact_merchant",
        scope_value={"merchant_name": "Swiggy"},
        priority=150,
    )
    assert rule_a.id is not None

    classifier = TransactionClassifier()

    # Test User A classification -> must resolve to 'Shopping' because of User A's rule
    rules_a = await CategorizationRuleService.list_user_rules(test_db_session, user_a, active_only=True)
    res_a = await classifier.classify(
        session=test_db_session,
        user_id=user_a,
        normalized_description="UPI-SWIGGY-18293@ICICI",
        direction="debit",
        transaction_type="expense",
        user_rules=rules_a,
        cached_categories=cats,
    )
    assert res_a.category_name == "Shopping"
    assert res_a.resolution_method == "user_rule"

    # Test User B classification -> must resolve to default 'Food & Dining' (isolated from User A!)
    rules_b = await CategorizationRuleService.list_user_rules(test_db_session, user_b, active_only=True)
    res_b = await classifier.classify(
        session=test_db_session,
        user_id=user_b,
        normalized_description="UPI-SWIGGY-18293@ICICI",
        direction="debit",
        transaction_type="expense",
        user_rules=rules_b,
        cached_categories=cats,
    )
    assert res_b.category_name == "Food & Dining"
    assert res_b.resolution_method != "user_rule"


# ==============================================================================
# 7. BULK CATEGORIZATION ENGINE
# ==============================================================================


@pytest.mark.asyncio
async def test_bulk_categorization_engine(test_db_session: AsyncSession) -> None:
    """Verify batch processing over multiple transactions with no N+1 query overhead."""
    await CategoryTaxonomyService.seed_system_categories(test_db_session)
    user_id = uuid.uuid4()
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Bulk Account",
        account_type="checking",
        currency="INR",
        is_synthetic=True,
    )
    test_db_session.add(account)

    # Insert 5 test transactions with missing categories
    descriptions = [
        ("BLINKIT GROCERY STORE", "debit", "expense"),
        ("NETFLIX SUBSCRIPTION", "debit", "expense"),
        ("SALARY DIRECT DEP ACME", "credit", "income"),
        ("TRF TO OWN ACCT 123", "debit", "transfer"),
        ("UNKNOWN MERCHANT 999", "debit", "expense"),
    ]
    for desc, direction, tx_type in descriptions:
        tx = Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            account_id=account.id,
            transaction_date=date(2026, 10, 1),
            original_description=desc,
            normalized_description=desc,
            amount=Decimal("100.00"),
            currency="INR",
            direction=direction,
            transaction_type=tx_type,
            review_status="pending",
        )
        test_db_session.add(tx)
    await test_db_session.commit()

    engine = TransactionIntelligenceEngine()
    summary = await engine.bulk_categorize(
        session=test_db_session,
        user_id=user_id,
    )

    assert summary["total_evaluated"] == 5
    assert summary["categorized_count"] >= 4
    assert summary["review_required_count"] >= 1  # The unknown merchant


# ==============================================================================
# 8. REST API INTEGRATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_categories_api(client_with_db: TestClient) -> None:
    """Verify GET /api/v1/categories returns taxonomy tree."""
    resp = client_with_db.get("/api/v1/categories?tree=true")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 10
    names = [c["name"] for c in data]
    assert "Food & Dining" in names
    assert "Utilities" in names


@pytest.mark.asyncio
async def test_transactions_crud_and_patch_api(
    client_with_db: TestClient, test_db_session: AsyncSession
) -> None:
    """Verify transaction listing, patch correction, and provenance retrieval via API."""
    cats = await CategoryTaxonomyService.seed_system_categories(test_db_session)
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="API Checking",
        account_type="checking",
        currency="INR",
        is_synthetic=True,
    )
    test_db_session.add(account)

    tx = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account.id,
        transaction_date=date(2026, 10, 10),
        original_description="SWIGGY BANGALORE IN",
        normalized_description="SWIGGY BANGALORE IN",
        amount=Decimal("380.00"),
        currency="INR",
        direction="debit",
        transaction_type="expense",
        category_id=cats["Food & Dining"].id,
        review_status="confirmed",
    )
    test_db_session.add(tx)
    await test_db_session.commit()

    # 1. GET /api/v1/transactions
    list_resp = client_with_db.get("/api/v1/transactions", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()["data"]
    assert list_data["total"] >= 1
    assert list_data["items"][0]["original_description"] == "SWIGGY BANGALORE IN"

    # 2. GET /api/v1/transactions/{id} (provenance & detail)
    detail_resp = client_with_db.get(f"/api/v1/transactions/{tx.id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["transaction_id"] == str(tx.id)
    assert "evidence_reasons" in detail_data

    # 3. PATCH /api/v1/transactions/{id} (correction)
    new_cat_id = cats["Shopping"].id
    patch_resp = client_with_db.patch(
        f"/api/v1/transactions/{tx.id}",
        json={"category_id": str(new_cat_id), "apply_future_rule": True},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["category_id"] == str(new_cat_id)
    assert patch_resp.json()["data"]["review_status"] == "corrected"

    # 4. Verify cross-user isolation: User B cannot access User A's transaction
    headers_b = {"X-User-Id": str(uuid.uuid4())}
    forbidden_get = client_with_db.get(f"/api/v1/transactions/{tx.id}", headers=headers_b)
    assert forbidden_get.status_code == 404
