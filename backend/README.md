# PaisaFlow Backend — API Foundation, Ingestion & Transaction Intelligence Engine

PaisaFlow backend is built as a production-minded modular monolith using Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, RapidFuzz, and Pydantic v2.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── main.py                  # FastAPI application entry point, lifecycle, and exception handlers
│   ├── api/
│   │   ├── dependencies.py      # Route dependencies (user context, security checks)
│   │   └── v1/
│   │       ├── router.py        # Consolidated v1 API router
│   │       └── routes/
│   │           ├── health.py    # Health check route (GET /health, GET /api/v1/health)
│   │           ├── config.py    # Public configuration route (GET /api/v1/config)
│   │           ├── imports.py   # Statement ingestion, preview & confirmation routes
│   │           ├── categories.py# Category taxonomy routes (GET /categories)
│   │           ├── merchants.py # Merchant identities & alias patterns (GET /merchants)
│   │           ├── transactions.py # Filtering, detail, user correction & bulk-categorize routes
│   │           └── categorization_rules.py # User-specific learning rules routes
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings loaded from .env
│   │   ├── logging.py           # Structured logging configuration
│   │   └── exceptions.py        # Domain exceptions and standardized error envelopes
│   ├── db/
│   │   ├── base.py              # DeclarativeBase, constraint naming convention, TimestampMixin
│   │   ├── session.py           # AsyncPG async engine, session factory, connectivity ping
│   │   └── dependencies.py      # get_db dependency for route injection
│   ├── ingestion/               # Statement Ingestion & Normalization Pipeline (Phase 3)
│   │   ├── validators.py        # Upload size, extension & magic-byte signature validation
│   │   ├── file_detector.py     # Secure temporary file handling & type identification
│   │   ├── exceptions.py        # Ingestion-specific domain exceptions
│   │   ├── pipeline.py          # End-to-end statement parsing & normalization coordinator
│   │   ├── parsers/
│   │   │   ├── base.py          # BaseStatementParser, ParsedRow, ParseResult
│   │   │   ├── csv_parser.py    # Robust CSV parser (BOM, delimiters, signed amounts, aliases)
│   │   │   └── pdf_parser.py    # Tabular PDF parser (pdfplumber) & scanned document detection
│   │   └── normalization/
│   │       ├── date_normalizer.py       # Multi-format date parser (%d/%m/%Y, ISO, text)
│   │       ├── amount_normalizer.py     # Positive Decimal magnitudes, signs, parentheses
│   │       ├── merchant_normalizer.py   # Channel stripping (UPI/POS/NEFT) & canonical aliases
│   │       ├── transaction_classifier.py# Transfers (excluded), refunds, income & expenses
│   │       └── fingerprint.py           # Deterministic SHA-256 duplicate fingerprinting
│   ├── intelligence/            # Transaction Intelligence & Correction Engine (Phase 4)
│   │   ├── engine.py            # Transaction intelligence coordinator & bulk execution
│   │   ├── categorization/
│   │   │   ├── taxonomy.py      # 15-parent canonical taxonomy & idempotent seeding
│   │   │   ├── rules.py         # Deterministic keyword & pattern rules
│   │   │   ├── confidence.py    # Calibrated confidence scoring (High/Medium/Low)
│   │   │   └── classifier.py    # Multi-tier classification precedence coordinator
│   │   ├── merchant/
│   │   │   ├── aliases.py       # Canonical merchant & alias catalogue
│   │   │   ├── resolver.py      # Exact, token boundary, and RapidFuzz fuzzy resolution
│   │   │   └── enrichment.py    # Merchant database persistence & alias linking
│   │   ├── corrections/
│   │   │   ├── correction_service.py # Immutable correction tracking & reversion
│   │   │   └── learning_rules.py     # User-specific categorization rule management
│   │   └── explanations/
│   │       └── explanation_service.py# Structured explainability provenance generator
│   ├── models/                  # SQLAlchemy 2 declarative models
│   │   ├── user.py              # User entity
│   │   ├── demo_profile.py      # Synthetic persona profile
│   │   ├── account.py           # Financial account entity
│   │   ├── category.py          # Category taxonomy hierarchy
│   │   ├── merchant.py          # Merchants and alias patterns
│   │   ├── transaction.py       # Financial transactions (NUMERIC precision)
│   │   ├── import_batch.py      # Ingestion batches, row counts, and preview state
│   │   ├── categorization_rule.py # User-scoped personalized classification rules
│   │   ├── transaction_correction.py # Audit log of category overrides & revisions
│   │   ├── recurring_commitment.py # Recurring obligations, observations, price changes
│   │   ├── financial_fact.py    # Living Money Model facts & snapshots
│   │   ├── goal.py              # Savings targets and progress
│   │   └── scenario.py          # What-if simulations
│   ├── schemas/                 # Pydantic request/response validation schemas
│   │   ├── common.py            # Standard ApiResponse and ApiError envelopes
│   │   ├── category.py          # Category taxonomy schemas
│   │   ├── merchant.py          # Merchant and alias schemas
│   │   ├── categorization_rule.py # Rule creation, update, preview & correction schemas
│   │   ├── transaction.py       # Filtering, pagination, patch & explanation schemas
│   │   └── import_batch.py      # Upload, preview, candidate row, and confirm schemas
│   ├── services/
│   │   ├── demo_data_service.py # Deterministic synthetic data generator & safe reset
│   │   └── import_service.py    # Import lifecycle, preview generation & idempotent confirmation
│   └── tests/                   # Pytest test suite (43 automated tests)
│       ├── conftest.py          # Test fixtures and in-memory test database
│       ├── test_app.py          # App lifecycle, routing, and secret leak verification
│       ├── test_models.py       # Metadata, foreign keys, constraints, and NUMERIC types
│       ├── test_synthetic_data.py # Seeding, edge cases, idempotency, and reset safety
│       ├── test_ingestion.py    # Security, parsers, normalization, duplicate & API tests
│       ├── test_intelligence.py # Taxonomy, merchants, confidence, rules, corrections & bulk tests
│       └── fixtures/
│           └── statements/      # 9 synthetic CSV and PDF statement fixtures
├── migrations/                  # Alembic database migrations
│   ├── env.py                   # Async Alembic environment
│   ├── script.py.mako           # Migration template
│   └── versions/
│       ├── 0001_initial_schema.py    # Initial transactional schema
│       ├── 0002_add_import_batches.py# Import batches schema and indexes
│       └── 0003_add_categorization_and_corrections.py # Rules and corrections tables
├── scripts/
│   ├── seed_demo_data.py                 # Idempotent seeding script for Asha Mehta & Kabir Shah
│   ├── reset_demo_data.py                # Safe reset script restricted to synthetic records
│   └── generate_synthetic_statements.py  # Generates 9 test CSV and PDF statements
├── alembic.ini                  # Alembic migration configuration
├── pytest.ini                   # Pytest asyncio configuration
└── requirements.txt             # Pinned backend dependencies
```

---

## 2. Transaction Intelligence Engine (Phase 4)

### Category Taxonomy
Implements a 15-parent canonical taxonomy with parent-child relationships and idempotent database seeding:
`Income`, `Refunds`, `Transfers`, `Housing & Rent`, `Utilities`, `Food & Dining`, `Transportation`, `Shopping`, `Healthcare`, `Education`, `Entertainment & Subscriptions`, `Travel`, `Financial Charges`, `Investments`, `Other`.

### Classification Precedence
1. **User Rules (Priority 150)**: Personalized overrides learned from corrections or created by the user (`CategorizationRule`). User rules never leak across users.
2. **Deterministic Type Overrides**: Transfers $\rightarrow$ `Transfers` (`Own Account Transfer` / `Peer-to-Peer Transfer`) with `is_excluded=True`. Refunds $\rightarrow$ `Refunds` (`Merchant Refund`), never ordinary income.
3. **Merchant Canonical Categories**: Exact alias, normalized name, token boundary, or RapidFuzz fuzzy match ($\ge 85$ score with 10-point collision margin) mapping to declared merchant categories.
4. **Deterministic Keyword Patterns**: Regex pattern rules for common utilities, dining, transit, healthcare, and fees.
5. **Fallback / Uncategorized State**: Flagged for user review (`review_status='flagged'`).

### Confidence Scoring
- **High ($\ge 0.80$)**: Automatic categorization without review.
- **Medium ($0.50 \le s < 0.80$)**: Review-required categorization.
- **Low ($< 0.50$)**: Uncategorized or flagged transaction.

### User Correction Engine & Audit History
- Preserves immutable financial facts: transaction amount, currency, transaction date, and direction cannot be changed.
- Records old and new values in `transaction_corrections` for explainability.
- Supports reverting corrections back to the previous classification state.
- Supports optional rule creation (`apply_future_rule=True`) to automatically categorize future occurrences.

---

## 3. Database Migrations (Alembic)

```bash
# Run migrations in online mode (requires active PostgreSQL connection)
alembic -c backend/alembic.ini upgrade head

# Generate static SQL in offline mode (does not require live connection)
alembic -c backend/alembic.ini upgrade head --sql

# Rollback one migration
alembic -c backend/alembic.ini downgrade -1
```

---

## 4. Running the API Server

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base: `http://127.0.0.1:8000`
- Interactive Swagger: `http://127.0.0.1:8000/docs`
- Categories: `GET /api/v1/categories`
- Merchants: `GET /api/v1/merchants`
- Transactions: `GET /api/v1/transactions`, `GET /api/v1/transactions/{id}`, `PATCH /api/v1/transactions/{id}`
- Bulk Categorization: `POST /api/v1/transactions/bulk-categorize`
- Categorization Rules: `GET /api/v1/categorization-rules`, `POST /api/v1/categorization-rules`, `PATCH /api/v1/categorization-rules/{id}`, `POST /api/v1/categorization-rules/{id}/undo`

---

## 5. Testing & Quality Verification

```bash
# Run all automated tests (43 unit, intelligence, ingestion, and API tests)
python -m pytest backend/app/tests -v

# Run Ruff linter
python -m ruff check backend
```
