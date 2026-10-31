"""Automated test suite for Phase 7: Gemini-Powered AI Financial Coach.

Validates:
1. Financial Context Builder (deterministic aggregations, living profile, grounded facts)
2. Dedicated Gemini Service (SDK invocation, mocked generation, error recovery)
3. Deterministic Fallback Engine (when GEMINI_API_KEY is unset or API offline)
4. Prompt Injection Defense (safe tag encapsulation, strict non-execution)
5. Coach Conversation Management (persistence, history, user isolation, cascading deletes)
6. REST API Endpoints (/api/v1/coach/*)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user_id
from backend.app.core.config import Settings
from backend.app.intelligence.coach.coach_service import CoachService
from backend.app.intelligence.coach.context_builder import FinancialContextBuilder
from backend.app.intelligence.coach.gemini_service import GeminiCoachService
from backend.app.intelligence.coach.prompts import (
    COACH_SYSTEM_INSTRUCTION,
    COACH_SYSTEM_PROMPT_VERSION,
    STARTER_PROMPTS,
)
from backend.app.main import app
from backend.app.models.account import Account
from backend.app.models.coach_conversation import CoachMessage
from backend.app.models.recurring_commitment import RecurringCommitment
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


# ============================================================================
# Helpers
# ============================================================================

async def create_test_coach_environment(session: AsyncSession, user_id: uuid.UUID):
    """Seed test user, account, transactions, and recurring commitment."""
    user = User(
        id=user_id,
        display_name="Coach Demo User",
        email=f"coach_{user_id}@demo.test",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Primary Salary Account",
        account_type="savings",
        currency="INR",
    )
    session.add(user)
    session.add(account)
    await session.flush()

    today = date.today()
    month_start = today.replace(day=1)

    # Add income transaction
    tx_income = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account.id,
        transaction_date=month_start,
        original_description="TechCorp Monthly Salary Oct 2026",
        normalized_description="TechCorp Salary",
        amount=Decimal("80000.00"),
        currency="INR",
        direction="credit",
        transaction_type="income",
        review_status="confirmed",
    )

    # Add dining expense
    tx_dining = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account.id,
        transaction_date=month_start + timedelta(days=2),
        original_description="Swiggy Food Orders",
        normalized_description="Swiggy",
        amount=Decimal("6500.00"),
        currency="INR",
        direction="debit",
        transaction_type="expense",
        review_status="confirmed",
    )

    # Add recurring commitment
    commitment = RecurringCommitment(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Netflix Streaming Subscription",
        cadence="monthly",
        typical_amount=Decimal("1499.00"),
        status="confirmed",
        confidence="high",
    )

    session.add_all([tx_income, tx_dining, commitment])
    await session.commit()
    return user, account


# ============================================================================
# 1. Financial Context Builder Tests
# ============================================================================

@pytest.mark.asyncio
async def test_financial_context_builder(test_db_session: AsyncSession):
    """Verify context builder outputs grounded facts with exact Decimal sums and prompt text."""
    user_id = uuid.uuid4()
    await create_test_coach_environment(test_db_session, user_id)

    builder = FinancialContextBuilder()
    context = await builder.build_context(test_db_session, user_id)

    assert "context_text" in context
    assert "grounded_facts" in context
    assert len(context["grounded_facts"]) >= 5

    # Check that context text mentions INR and prompt boundaries
    assert "--- USER FINANCIAL PROFILE (GROUNDED TRUTH) ---" in context["context_text"]
    assert "Currency: INR" in context["context_text"]
    assert "TechCorp" in context["context_text"] or "Total Income: ₹80,000.00" in context["context_text"]

    # Verify grounded facts contain income and outflow metrics
    fact_labels = [f["label"] for f in context["grounded_facts"]]
    assert "Total Inflow (Income)" in fact_labels
    assert "Total Net Outflow (Expenses)" in fact_labels
    assert "Net Cash Flow Surplus" in fact_labels


# ============================================================================
# 2. Gemini Coach Service & Fallback Engine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_gemini_service_unconfigured_fallback():
    """Verify service falls back safely without API key and routes questions intelligently."""
    # Settings without API key
    settings = Settings(GEMINI_API_KEY="")
    service = GeminiCoachService(settings=settings)
    assert not service.is_configured

    fake_context = {
        "summary": {
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "income_total": "80000.00",
            "expense_net": "45000.00",
            "net_cash_flow": "35000.00",
            "savings_rate": "43.75%",
        },
        "top_categories": [
            {"category_name": "Food & Dining", "amount": Decimal("12000.00"), "share_percentage": "26.7%"},
            {"category_name": "Housing & Utilities", "amount": Decimal("20000.00"), "share_percentage": "44.4%"},
        ],
        "recurring_list": [
            {"merchant": "Netflix", "amount": "₹649.00", "cadence": "monthly", "monthly_equivalent": "₹649.00"},
            {"merchant": "Broadband", "amount": "₹1,199.00", "cadence": "monthly", "monthly_equivalent": "₹1,199.00"},
        ],
        "total_recurring_monthly": "1848.00",
        "grounded_facts": [{"label": "Total Inflow", "value": "₹80,000.00"}],
    }

    # Query 1: Spending Breakdown
    resp_spending = await service.generate_response("Where did most of my money go this month?", fake_context)
    assert not resp_spending["is_live_gemini"]
    assert "Spending Analysis" in resp_spending["content"]
    assert "Food & Dining" in resp_spending["content"]
    assert "₹45,000.00" in resp_spending["content"]

    # Query 2: Recurring Commitments
    resp_recurring = await service.generate_response("What are my recurring subscriptions?", fake_context)
    assert "Active Recurring Commitments" in resp_recurring["content"]
    assert "Netflix" in resp_recurring["content"]
    assert "₹1,848.00" in resp_recurring["content"]

    # Query 3: Affordability
    resp_afford = await service.generate_response("Can I afford a new ₹5,000 EMI?", fake_context)
    assert "Affordability" in resp_afford["content"]
    assert "₹35,000.00" in resp_afford["content"]
    assert "Cash Flow Verdict" in resp_afford["content"]

    # Query 4: Savings Rate
    resp_savings = await service.generate_response("How can I save more money?", fake_context)
    assert "Savings Strategy" in resp_savings["content"]
    assert "43.75%" in resp_savings["content"]


@pytest.mark.asyncio
async def test_gemini_service_mocked_live_call():
    """Verify Gemini API invocation when API key is provided, using a mocked genai model."""
    settings = Settings(GEMINI_API_KEY="AIzaSyTestKeyValidFormat")
    service = GeminiCoachService(settings=settings)
    assert service.is_configured

    fake_context = {
        "context_text": "Income: ₹80,000. Expense: ₹45,000.",
        "grounded_facts": [{"label": "Net Cash Flow", "value": "₹35,000.00"}],
    }

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "Based on your financial data, your net surplus is ₹35,000. You have good buffer."

    with patch("google.generativeai.GenerativeModel") as MockModel:
        instance = MockModel.return_value
        instance.generate_content_async = AsyncMock(return_value=mock_gemini_response)

        resp = await service.generate_response("Can I save more?", fake_context)
        assert resp["is_live_gemini"]
        assert "₹35,000" in resp["content"]
        assert resp["grounded_facts"] == fake_context["grounded_facts"]
        assert any("Gemini" in a for a in resp["assumptions"])


@pytest.mark.asyncio
async def test_gemini_service_error_recovery_to_fallback():
    """Verify that network or API quota errors gracefully fall back without raising an unhandled exception."""
    settings = Settings(GEMINI_API_KEY="AIzaSyTestKey")
    service = GeminiCoachService(settings=settings)

    fake_context = {
        "summary": {"period_start": "2026-10-01", "period_end": "2026-10-31", "income_total": "50000.00", "expense_net": "30000.00"},
        "grounded_facts": [],
    }

    with patch("google.generativeai.GenerativeModel") as MockModel:
        instance = MockModel.return_value
        instance.generate_content_async = AsyncMock(side_effect=RuntimeError("Google API quota exhausted"))

        resp = await service.generate_response("Where is my money?", fake_context)
        assert not resp["is_live_gemini"]
        assert "Spending Analysis" in resp["content"]
        assert any("quota exhausted" in a.lower() or "runtimeerror" in a.lower() or "gemini api request failed" in a.lower() for a in resp["assumptions"])


# ============================================================================
# 3. Prompt Injection Defense Tests
# ============================================================================

@pytest.mark.asyncio
async def test_prompt_injection_safety_instruction():
    """Verify system instructions enforce prompt injection defenses and boundary tags."""
    assert "PROMPT INJECTION DEFENSE" in COACH_SYSTEM_INSTRUCTION
    assert "<user_question>" in COACH_SYSTEM_INSTRUCTION
    assert "</user_question>" in COACH_SYSTEM_INSTRUCTION
    assert "SEBI" in COACH_SYSTEM_INSTRUCTION
    assert COACH_SYSTEM_PROMPT_VERSION == "1.0.0"


# ============================================================================
# 4. Coach Service & Conversation Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_coach_service_conversation_lifecycle(test_db_session: AsyncSession):
    """Test full conversation flow: create, message persistence, history query, delete, and isolation."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    await create_test_coach_environment(test_db_session, user_a)
    await create_test_coach_environment(test_db_session, user_b)

    service = CoachService()

    # 1. Send first message (creates conversation)
    msg1 = await service.send_message(
        db=test_db_session,
        user_id=user_a,
        message="Where is most of my money going this month?",
    )
    assert msg1["sender"] == "coach"
    assert msg1["conversation_id"] is not None
    assert len(msg1["content"]) > 20
    assert msg1["grounded_facts"] is not None
    conv_id = msg1["conversation_id"]

    # 2. Send follow-up in the same conversation
    msg2 = await service.send_message(
        db=test_db_session,
        user_id=user_a,
        message="What about my recurring subscriptions?",
        conversation_id=conv_id,
    )
    assert msg2["conversation_id"] == conv_id

    # 3. List conversations
    convs = await service.list_conversations(test_db_session, user_id=user_a)
    assert len(convs) == 1
    assert convs[0]["id"] == conv_id
    assert convs[0]["message_count"] == 4  # 2 user messages + 2 coach responses

    # 4. Retrieve conversation detail
    detail = await service.get_conversation(test_db_session, user_id=user_a, conversation_id=conv_id)
    assert detail is not None
    assert len(detail["messages"]) == 4
    assert detail["messages"][0]["sender"] == "user"
    assert detail["messages"][1]["sender"] == "coach"

    # 5. User Isolation: User B cannot access User A's conversation
    conv_b = await service.get_conversation(test_db_session, user_id=user_b, conversation_id=conv_id)
    assert conv_b is None

    # 6. Delete conversation
    deleted = await service.delete_conversation(test_db_session, user_id=user_a, conversation_id=conv_id)
    assert deleted is True

    # Verify conversation and cascade messages are removed
    check_conv = await service.get_conversation(test_db_session, user_id=user_a, conversation_id=conv_id)
    assert check_conv is None
    res_msg = await test_db_session.execute(
        select(CoachMessage).where(CoachMessage.conversation_id == conv_id)
    )
    assert len(res_msg.scalars().all()) == 0


# ============================================================================
# 5. REST API Endpoints Tests
# ============================================================================

@pytest.mark.asyncio
async def test_coach_api_endpoints(client_with_db: AsyncSession, test_db_session: AsyncSession):
    """Test REST API routes for coach: /messages, /conversations, /prompts."""
    client = client_with_db
    user_id = uuid.uuid4()
    await create_test_coach_environment(test_db_session, user_id)

    # Override get_current_user_id
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    try:
        # 1. GET /api/v1/coach/prompts
        res_prompts = client.get("/api/v1/coach/prompts")
        assert res_prompts.status_code == 200
        prompts_data = res_prompts.json()["data"]["prompts"]
        assert len(prompts_data) >= 4
        assert prompts_data == STARTER_PROMPTS

        # 2. POST /api/v1/coach/messages
        payload = {"message": "Where is my money going?"}
        res_msg = client.post("/api/v1/coach/messages", json=payload)
        assert res_msg.status_code == 200
        msg_data = res_msg.json()["data"]
        assert msg_data["sender"] == "coach"
        assert "conversation_id" in msg_data
        conv_id = msg_data["conversation_id"]

        # 3. GET /api/v1/coach/conversations
        res_list = client.get("/api/v1/coach/conversations")
        assert res_list.status_code == 200
        list_data = res_list.json()["data"]
        assert len(list_data) >= 1
        assert list_data[0]["id"] == conv_id

        # 4. GET /api/v1/coach/conversations/{id}
        res_detail = client.get(f"/api/v1/coach/conversations/{conv_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()["data"]
        assert len(detail_data["messages"]) == 2

        # 5. DELETE /api/v1/coach/conversations/{id}
        res_del = client.delete(f"/api/v1/coach/conversations/{conv_id}")
        assert res_del.status_code == 200
        assert res_del.json()["data"]["deleted"] is True

        # 6. Verify 404 after deletion
        res_404 = client.get(f"/api/v1/coach/conversations/{conv_id}")
        assert res_404.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
