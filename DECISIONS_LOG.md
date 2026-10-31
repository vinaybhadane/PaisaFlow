# PaisaFlow — Architecture and Product Decisions Log

## Decision template
### ADR-XXX — Title
- Status: Proposed / Accepted / Superseded
- Date:
- Context:
- Decision:
- Alternatives:
- Consequences:
- Related docs:

## ADR-001 — Synthetic data only
- Status: Accepted
- Context: Hackathon requires synthetic financial data.
- Decision: All demo records are fictional; no real bank or inbox integrations.
- Consequence: Future extensibility is allowed, but real data is prohibited in the hackathon build.

## ADR-002 — Deterministic financial calculations
- Status: Accepted
- Context: LLM arithmetic is not sufficiently reliable as source of truth.
- Decision: Backend services calculate all totals and scenarios with Decimal.
- Consequence: Gemini explains validated outputs.

## ADR-003 — Modular monolith
- Status: Accepted
- Context: Hackathon needs speed and reliability.
- Decision: Modular FastAPI backend plus separate worker, not microservices.
- Consequence: Simpler deployment and clear domain boundaries.

## ADR-004 — PostgreSQL source of truth
- Status: Accepted
- Context: Financial records require relational integrity and history.
- Decision: PostgreSQL stores canonical records; pgvector only for optional contextual retrieval.
- Consequence: NUMERIC, foreign keys, migrations and indexes required.

## ADR-005 — Azure cloud direction
- Status: Accepted
- Context: Project owner has Azure for Students.
- Decision: Prefer Azure where current credit, cost and availability permit.
- Consequence: Verify all service pricing before provisioning.

## ADR-006 — Gemini for language assistance
- Status: Accepted
- Context: Conversational coaching is useful, but numeric correctness is critical.
- Decision: Gemini explains and structures language; backend tools supply financial facts and arithmetic.
- Consequence: Validate model outputs and numeric claims.

## ADR-007 — UI library integration: SmoothUI and Unlumen UI
- Status: Accepted
- Date: 2026-10-31
- Context: PaisaFlow requires polished interactive CTA controls and contextual tooltips (for confidence, synthetic disclosures, and provenance) integrated into Next.js 15 App Router with Tailwind CSS v4 and Motion.
- Decision: Install `smooth-button` via SmoothUI CLI and `floating-tooltip` via Unlumen UI (shadcn registry) directly as source components in `frontend/components/`. Configure path aliases and unified `@/lib/utils` `cn` helper.
- Consequences: Retains complete source control, strict TypeScript compliance, zero hydration issues, and clean Next.js production builds.
- Related docs: `docs/17_FRONTEND_UI_LIBRARIES.md`, `frontend/README.md`.

## ADR-008 — Async PostgreSQL, Alembic Offline DDL, and In-Memory Unit Test Isolation
- Status: Accepted
- Date: 2026-10-31
- Context: Backend requires strict PostgreSQL types (UUID, NUMERIC(18, 2), JSONB, compound indexes) with SQLAlchemy 2 asyncpg and Alembic migrations, while allowing continuous testing and verification in environments where a live PostgreSQL daemon or Docker service may not yet be running.
- Decision: Use asyncpg engine for runtime and Alembic migrations targeting PostgreSQL. Verify migrations using Alembic offline transactional SQL generation (`alembic upgrade head --sql`). Structure models with generic JSON types having JSONB PostgreSQL variants, allowing isolated in-memory unit testing for seeding, idempotency, and reset validation without substituting SQLite as the application architecture.
- Consequences: Preserves 100% PostgreSQL schema integrity for deployment while ensuring reliable CI/CD and developer testing.
- Related docs: `docs/08_DATABASE_SCHEMA.md`, `docs/14_TESTING_ACCEPTANCE.md`.

## ADR-009 — Statement Ingestion, Canonical Normalization, and Preview-Commit Lifecycle
- Status: Accepted
- Date: 2026-10-31
- Context: Financial statement ingestion must accept varied CSV and text-based PDF formats, handle malformed rows and date/currency variations, protect against malicious uploads, detect potential duplicate transactions deterministically, and provide a non-destructive user preview before committing records into user accounts.
- Decision:
  1. Build modular pipeline with secure upload validation (10MB limit, magic byte signature detection, path traversal sanitization).
  2. Implement heuristic column detection supporting standard, alternate, and signed amount representations.
  3. Canonical normalization: always parse monetary amounts to positive Python Decimals with explicit direction ('debit'/'credit') and transaction type ('expense', 'income', 'transfer', 'refund', 'fee').
  4. Internal transfers (e.g., own-account transfers) are flagged with `is_excluded=True` to prevent double-counting in net income/expense calculations; refunds are explicitly distinguished from ordinary salary/deposit income.
  5. Deterministic SHA-256 fingerprinting based on user/account, date, amount, direction, and description identifies exact duplicates without deleting repeated legitimate transactions.
  6. Two-phase import workflow: `POST /api/v1/imports` produces an auditable, non-destructive preview with row-level validation; `POST /api/v1/imports/{id}/confirm` idempotently commits approved rows within an atomic database transaction.
- Consequences:
  1. Completely eliminates floating-point monetary arithmetic and silent data corruption.
  2. Protects user autonomy by providing clear provenance and pre-commit auditability.
  3. Ensures idempotent retries without duplicate transaction insertions.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-010 — Transaction Intelligence, Confidence Calibration, and User Correction Architecture
- Status: Accepted
- Date: 2026-10-31
- Context: Financial transactions require accurate, explainable categorization without fabricating financial categories, mixing refunds with ordinary income, or treating own-account transfers as expenses. The system must support personalized user corrections that take precedence over generic rules, while never modifying immutable financial facts (amount, date, direction).
- Decision:
  1. Implement a 15-parent canonical taxonomy with typed parent-child relationships and idempotent seeding.
  2. Implement multi-tier categorization precedence:
     - Priority 1: User-specific explicit rules (`CategorizationRule`)
     - Priority 2: Deterministic type rules (transfers $\rightarrow$ Transfers with `is_excluded=True`, refunds $\rightarrow$ Refunds)
     - Priority 3: Merchant resolution (exact alias $\rightarrow$ normalized $\rightarrow$ token boundary $\rightarrow$ RapidFuzz $\ge 85$ with 10-point collision margin)
     - Priority 4: Deterministic keyword and pattern rules
     - Priority 5: Fallback uncategorized state requiring review (`review_status='flagged'`)
  3. Calibrate confidence scores:
     - High ($\ge 0.80$): automatic confirmation without review
     - Medium ($0.50 \le s < 0.80$): review-required
     - Low ($< 0.50$): uncategorized or flagged
  4. User correction workflow: preserves immutable financial facts (amount, currency, transaction_date, direction), logs previous and new values in `transaction_corrections` for explainability, allows reverting corrections, and optionally synthesizes a user-scoped future rule (`CategorizationRule`).
  5. Bulk categorization operates on preloaded taxonomy and user rules to eliminate N+1 database queries.
- Consequences:
  1. High classification accuracy with zero AI API key dependency.
  2. Complete auditability and provenance for every categorized transaction.
  3. Total isolation of user-specific rules preventing cross-user rule leakage.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/08_DATABASE_SCHEMA.md`, `docs/09_AI_INTELLIGENCE_ENGINE.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-011 — Living Money Model, Recurring Pattern Intelligence, and Effective-Dated Financial Facts
- Status: Accepted
- Date: 2026-10-31
- Context: PaisaFlow requires an authoritative, continuously updated financial profile (Living Money Model) reflecting actual recurring obligations (subscriptions, rent, utilities, loan EMIs, recurring income) and user financial facts (income, fixed costs, savings balance). Financial arithmetic must be deterministic with Python `Decimal`, and user-confirmed facts must strictly override inferred patterns without erasing historical auditability.
- Decision:
  1. **Calendar-Aware Cadence Detection**:
     - Evaluates weekly (~7d), fortnightly (~14d), monthly (calendar-aware 26–35d with month-length differences like Jan 31/Feb 28 and weekend posting shifts), quarterly (~90d / 3mo), half-yearly (~180d / 6mo), and yearly (~365d / 12mo).
     - Irregular patterns ($CV > 0.35$) are flagged as `cadence='custom'` and strictly withheld from receiving an invented `next_expected_date`.
     - 1 observation cannot establish recurrence; 2 observations create a provisional candidate (`status='likely'`, `confidence='low'`); $\ge 3$ regular observations create high-confidence commitments.
  2. **Amount Analysis & Monthly Planning Equivalents**:
     - Stable (< 5% spread) vs. variable ($\ge 5\%$ spread) classification.
     - Authoritative planning equivalents from `docs/10_FINANCIAL_LOGIC.md`:
       - Monthly: `typical_amount`
       - Weekly: `typical_amount * 52 / 12`
       - Fortnightly: `typical_amount * 26 / 12`
       - Quarterly: `typical_amount / 3`
       - Half-yearly: `typical_amount / 6`
       - Yearly: `typical_amount / 12`
       - Annual cost: `monthly_equivalent * 12` (all `Decimal`).
  3. **Price Change Intelligence**:
     - Materiality threshold: absolute change $\ge ₹10.00$ or percentage change $\ge 2.0\%$.
     - Single change is flagged as `status='possible'` ("possible amount change"), never assumed confirmed without user review.
     - Persistent shifts across $\ge 2$ observations are tracked with full change direction, percentage, and baseline evidence.
  4. **Financial Fact Resolution & Provenance**:
     - Precedence order: `user_confirmed` (100) > `scenario_assumption` (50) > `transaction_inferred` (30) > `system_calculated` (20).
     - User-confirmed facts strictly override inferred facts during overlapping periods.
     - Non-destructive updates: updating a fact closes prior active fact's `effective_to`, preserving historical reproducibility.
  5. **Deterministic Financial Summaries & Profile Snapshots**:
     - Excludes own-account transfers from income/expense.
     - Adjusts net expenses with refunds.
     - Calculates cash-flow savings rate only when income is positive.
     - Available money (discretionary surplus): `effective_income - recurring_monthly_commitments - essential_living_expenses`.
     - Periodic profile snapshots (`profile_snapshots`) are immutable and recomputed idempotently. Month-over-month comparisons produce deterministic deltas and narrative diffs.
- Consequences:
  1. 100% deterministic calculations; zero reliance on LLMs for financial numbers.
  2. Complete historical audit trail for facts and recurring commitments.
  3. Users maintain full control to confirm, reject, or adjust recurring obligations and financial facts.
- Related docs: `docs/08_DATABASE_SCHEMA.md`, `docs/09_AI_INTELLIGENCE_ENGINE.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-012 — Financial Insights, Forecasting & What-If Simulation Engine
- Status: Accepted
- Date: 2026-10-31
- Context: Users require explainable financial observations, category spending analysis, multi-month forecasting, and hypothetical What-If simulations to understand the future impact of financial decisions (reducing dining expenses, cancelling subscriptions, salary raises, adding loan EMIs). Simulations must never alter historical transactions or confirmed living facts, calculations must be 100% deterministic using Python `Decimal`, and forecasts must be transparent about data coverage without presenting estimates as guaranteed outcomes.
- Decision:
  1. **Spending Analyzer & Concentration**:
     - Calculates monthly category totals, percentages, and prior period MoM comparisons.
     - Segregates spending into Essential Needs (housing, utilities, groceries, healthcare, debt/EMI, transport) vs Discretionary Wants.
     - Refunds reduce net expenses; own-account transfers are strictly excluded from spend totals.
     - Detects spending trends ("increasing", "decreasing", "stable") with materiality thresholds ($\ge ₹50$ and $\ge 5\%$).
  2. **Financial Insights Engine**:
     - Generates grounded, evidence-backed insights: `highest_spending_category`, `unusual_spending_increase` ($\ge ₹1,000$ and $\ge 20\%$), `income_vs_expense` (surplus vs deficit), `savings_rate_trend`, `essential_vs_discretionary`, and `recurring_payment_burden`.
     - Strict data coverage guard: returns an educational coverage notice when transaction count $< 3$ to avoid generating misleading observations from insufficient data.
  3. **Deterministic Financial Forecaster**:
     - Projects monthly cash flow, expected recurring obligations, variable spend run-rate, projected net cash flow, and cumulative savings for 1, 3, and 6 months ahead.
     - Separate baseline actuals from forward estimates; explicitly discloses assumptions (zero investment return, stable run-rate, non-guarantee).
  4. **What-If Simulation Engine & Immutability**:
     - Supported scenario templates: `reduce_category_percentage` ($B \times (1 - p/100)$), `reduce_category_fixed` ($\max(B - R, 0)$), `cancel_recurring` (monthly planning equivalent savings with explicit note that cancellation is hypothetical and not performed with merchant), `income_change`, `add_expense`, `custom_savings`.
     - Multi-horizon evaluation across 3, 6, and 12-month cumulative periods.
     - Scenarios are isolated in `scenarios` table; actual transactions and user financial facts are 100% immutable.
     - Supports scenario CRUD and side-by-side multi-scenario comparison.
  5. **Frontend Integration**:
     - Added `/dashboard` with tabbed views for Insights, Spending Breakdown, Deterministic Forecasts, and Interactive What-If Simulator with real API calls, loading skeletons, error handling, and clean responsive styling.
- Consequences:
  1. Complete adherence to non-negotiable principles: zero LLM arithmetic; pure Decimal precision.
  2. Full user autonomy to test financial decisions before committing money.
  3. Strict isolation between hypothetical scenarios and immutable transaction records.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/08_DATABASE_SCHEMA.md`, `docs/09_AI_INTELLIGENCE_ENGINE.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-013 — Gemini-Powered AI Financial Coach with Grounded Context and Deterministic Fallback Engine
- Status: Accepted
- Date: 2026-10-31
- Context: Users need an intuitive, conversational financial coach to ask questions about where their money is going, evaluate affordability of new commitments or EMIs, analyze recurring subscription burden, and explore ways to improve savings. Per PaisaFlow non-negotiable principles (`AGENTS.md` and `docs/09_AI_INTELLIGENCE_ENGINE.md`), an LLM must never calculate money, balances, or forecasts; all numbers must originate from backend deterministic Python `Decimal` engines; user input must be protected against prompt injection; and the system must gracefully fall back to local deterministic templates if the Gemini API key is unconfigured or network requests fail.
- Decision:
  1. **Financial Context Builder (`context_builder.py`)**:
     - Prepares strictly bounded, user-isolated context before calling Gemini.
     - Injects current period income, expenses, net surplus, savings rate, top spending categories, active recurring obligations, living model facts, algorithmic insights, and 3-month deterministic forecast.
     - Extracts structured `grounded_facts` list attached to every response for transparent UI citation and auditability.
  2. **System Prompt & Safety Guardrails (`prompts.py`)**:
     - System prompt version `1.0.0` with empathetic, objective Indian personal finance coach persona (INR, ₹, lakhs/crores formatting).
     - Strict non-negotiables: informational coaching only; never recommend specific securities, stocks, or crypto assets; never claim to execute real bank payments or cancellations; never request bank credentials or UPI PINs.
     - Prompt injection defense: user queries are encapsulated in `<user_question>` delimiters with explicit instructions forbidding instruction leakage, role override, or code execution.
  3. **Dedicated Gemini Service & Fallback Engine (`gemini_service.py`)**:
     - Reads `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-1.5-flash`).
     - Low temperature ($0.2$) for factual grounding and low hallucination.
     - When `GEMINI_API_KEY` is empty, unset, or if API quota/network requests fail, seamlessly executes deterministic rule-based template generation without throwing 500 errors.
     - Supports specialized deterministic fallback branches: spending breakdown, recurring commitments, affordability/EMI evaluation, savings strategy, and forecasting.
  4. **Conversation Persistence & Isolation (`coach_conversation.py`, migration `0004`)**:
     - `coach_conversations` and `coach_messages` SQLAlchemy models and Alembic migration `0004_add_coach_conversations`.
     - Automatic thread title generation from user's first query.
     - Enforces strict user ownership; deleting a conversation cascades through all messages.
  5. **REST API Endpoints (`/api/v1/coach/*`)**:
     - `POST /api/v1/coach/messages`: Submits user query and returns grounded coach response.
     - `GET /api/v1/coach/conversations`: Lists user conversations with message counts.
     - `GET /api/v1/coach/conversations/{conversation_id}`: Retrieves ordered message history.
     - `DELETE /api/v1/coach/conversations/{conversation_id}`: Deletes conversation thread.
     - `GET /api/v1/coach/prompts`: Returns curated starter exploration questions.
  6. **Frontend Dashboard Integration (`dashboard/page.tsx`)**:
     - Added "💬 AI Financial Coach" tab in Next.js dashboard with starter prompt chips, interactive message thread, grounded facts pills, live Gemini vs deterministic engine status badge, and conversation thread switcher.
- Consequences:
  1. 100% adherence to financial correctness; zero LLM arithmetic.
  2. Seamless zero-dependency operation: functions fully offline with deterministic templates if Gemini is not configured.
  3. Complete auditability with cited grounded facts and clear disclaimers.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/08_DATABASE_SCHEMA.md`, `docs/09_AI_INTELLIGENCE_ENGINE.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-014 — Complete Product Integration, Multi-View Dashboard, and Demo Persona Switcher
- Status: Accepted
- Date: 2026-10-31
- Context: Phases 1 through 7 delivered robust backend intelligence engines (statement ingestion, transaction intelligence, living money model, recurring pattern detector, forecasting, what-if simulations, Gemini coach). However, the frontend remained fragmented with disjointed views, lack of interactive statement upload and review workflows, absence of transaction categorization correction controls, and no direct mechanism to toggle between seeded synthetic personas (Asha Mehta vs. Kabir Shah) to showcase differing financial profiles.
- Decision:
  1. **Demo Persona Switcher & User Isolation**:
     - Added `GET /api/v1/profile/personas` returning all seeded synthetic personas (`Asha Mehta`, `Kabir Shah`) with their monthly income and persona profile notes.
     - Extended frontend API client (`frontend/lib/api.ts`) with `setActiveUserId()` and `getActiveUserId()` stored in `localStorage` and dynamically injected via `X-User-Id` header into all requests.
     - Added persistent Persona Switcher dropdown in the dashboard header, enabling instant hot-swapping between Asha and Kabir.
  2. **Unified 8-Tab Application Dashboard (`frontend/app/dashboard/page.tsx`)**:
     - `overview`: Executive financial health KPI cards (Inflow, Outflow, Net Surplus, Savings Rate), Living Facts cards with source provenance and confidence badges, and quick-action navigation cards.
     - `imports`: Interactive CSV and text-based PDF drag-and-drop file upload, non-destructive import preview with duplicate detection badges (`new`, `duplicate_exact`, `duplicate_potential`), and single-click idempotent confirmation.
     - `transactions`: Full transaction ledger with search, category filtering, pagination, inline "Correct Category" modal with optional future rule creation, and "Why?" provenance modal explaining classification evidence.
     - `recurring`: Subscriptions and commitments dashboard displaying cadence, typical amount, monthly planning equivalent, annual projection, interactive confirm/reject review controls, and price-change alerts.
     - `insights`: Essential Needs vs Discretionary Wants distribution, top 5 spending categories with MoM trends, and algorithmic insights feed.
     - `forecast`: Deterministic multi-month projections (1, 3, 6-month horizons), projected monthly net cash flows, cumulative savings projections, and transparent assumptions disclosure.
     - `simulator`: Interactive scenario runner (reduce category %, reduce fixed ₹, hypothetical subscription cancellation, income changes), multi-horizon (3M, 6M, 12M) cumulative delta impact cards, and saved scenario management.
     - `coach`: Interactive conversational interface with Google Gemini (and local deterministic template fallback), starter exploration prompts, grounded fact citation pills, and multi-thread switcher.
  3. **UI/UX Polish & Library Integration**:
     - Utilized Unlumen UI `FloatingTooltip` for synthetic demo mode disclosure and confidence indicators.
     - Utilized SmoothUI interactive buttons for primary CTAs and responsive controls.
     - Strict Indian Rupee (`₹`) formatting and Decimal-derived monetary displays with zero floating-point arithmetic.
  4. **Landing Page Enhancement (`frontend/app/page.tsx`)**:
     - Added Quick Demo Persona launchers directly in the hero section, instantly configuring persona session and directing users into the live dashboard.
     - Added AI Coach feature showcase card in the product feature grid.
- Consequences:
  1. Fully unified, production-grade application integrating every backend capability into an intuitive user journey.
  2. Complete adherence to non-negotiables: synthetic financial data only, deterministic financial calculations, zero LLM arithmetic, and transparent provenance.
  3. Zero regressions: 80/80 pytest tests passing, 0 Ruff errors, 0 ESLint errors, and clean Next.js production build.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/04_USER_FLOWS.md`, `docs/05_UI_UX_GUIDELINES.md`, `docs/13_API_SPECIFICATION.md`, `docs/17_FRONTEND_UI_LIBRARIES.md`.

## ADR-015 — Gemini 3.5 Flash Lite Integration, Firebase Google Authentication, Zero-Fake-Data Ingestion, and Cinematic Dark Dashboard Parity
- Status: Accepted
- Date: 2026-10-31
- Context: User requested upgrading the AI coach to Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`), replacing demo persona accounts with real Firebase Google Authentication, removing all fake/seeded mock financial figures so that all figures originate 100% from uploaded statements, and unifying the dashboard visual styling with the cinematic black-and-silver dark theme established on the landing page without horizontal scrolling.
- Decision:
  1. **Gemini 3.5 Flash Lite Integration**:
     - Configured `gemini-3.5-flash-lite` in `.env`, `backend/app/core/config.py`, and `backend/app/intelligence/coach/gemini_service.py`.
     - Validated live generation with live Gemini API responses using the provided API key.
     - Preserved deterministic grounding: LLM interprets and explains, but all amounts, totals, and percentages are derived deterministically by Python `Decimal` backend logic.
  2. **Firebase Google Authentication**:
     - Installed and configured `firebase/app` and `firebase/auth` using the official PaisaFlow project credentials.
     - Implemented `loginWithGoogle()` and `logoutFirebase()` with Next.js SSR-safe multi-instance guarding.
     - Backend dependencies in `backend/app/api/dependencies.py` deterministically map Firebase UIDs to UUIDs via `uuid.uuid5(uuid.NAMESPACE_URL, f"firebase:{x_user_id}")` with automatic profile synchronization (`X-User-Email`, `X-User-Name`).
  3. **Zero Fake Data Architecture**:
     - Removed hardcoded fallback figures and fake persona statistics.
     - When a user logs in with zero uploaded statements, the dashboard accurately displays a zero-data clean state prompting for statement upload.
     - Provided `sample_statement.csv` in `/public` for instant verification of real statement ingestion.
  4. **Cinematic Dark Dashboard Overhaul**:
     - Matched the landing page design aesthetic: pure black `#000000`, white typography, subtle glassmorphic borders (`border-white/10` to `border-white/15`), and `#0A0A0A` card backgrounds.
     - Eliminated horizontal scrolling with responsive wrapping navigation chips (`overflow-x-hidden`).
     - Fully eliminated emojis in favor of crisp SVG Lucide icons.
- Consequences:
  1. Modern, authenticated FinTech user experience with live Google OAuth.
  2. Complete data authenticity: 100% of facts, recurring patterns, and cash flow figures originate from statement ingestion.
  3. Seamless Next.js static and SSR builds with 0 TypeScript and 0 ESLint errors.
- Related docs: `docs/03_FEATURE_SPECIFICATION.md`, `docs/09_AI_INTELLIGENCE_ENGINE.md`, `docs/10_FINANCIAL_LOGIC.md`, `docs/13_API_SPECIFICATION.md`.

## ADR-016 — Migration from Azure to Free Supabase PostgreSQL Database
- Status: Accepted
- Date: 2026-10-31
- Context: Azure Flexible Server PostgreSQL involves burstable billing, credit expiration risks, and firewall provisioning friction. The user requested replacing Azure services completely with Supabase's generous Free Tier. Because PaisaFlow's backend was built on standard SQLAlchemy, asyncpg, and Alembic migrations, migrating to Supabase requires zero code changes and provides a direct managed PostgreSQL instance with a web GUI table editor.
- Decision:
  1. Replaced Azure Cloud Storage and Key Vault settings in `backend/app/core/config.py` and `.env.example` with Supabase configuration parameters (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DATABASE_URL`).
  2. Standardized `DATABASE_URL` format to Supabase's asyncpg connection URI (`postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?ssl=require`).
  3. Updated `docs/16_AZURE_DEPLOYMENT.md` to `docs/16_SUPABASE_DEPLOYMENT.md` documenting the 100% free hosting stack (Supabase PostgreSQL + Firebase Auth + Google Gemini 3.5 Flash Lite + Vercel).
- Consequences:
  1. Zero recurring cloud fees or credit expiration anxiety.
  2. Instant browser GUI table inspection in Supabase Studio.
  3. Retains 100% test pass rate (80/80 backend pytest tests pass).
- Related docs: `docs/06_TECH_STACK.md`, `docs/08_DATABASE_SCHEMA.md`, `docs/16_AZURE_DEPLOYMENT.md`.

Add new ADRs below. Supersede accepted decisions explicitly rather than silently rewriting them.
