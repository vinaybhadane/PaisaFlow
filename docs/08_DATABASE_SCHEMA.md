# 08 — Database Schema and Data Model

## Conventions
PostgreSQL is the source of truth. Use UUID primary keys, `TIMESTAMPTZ` for timestamps, `DATE` for transaction/effective dates, `NUMERIC(18,2)` or appropriate precision for money, ISO currency codes and Alembic migrations. Every user-owned record has `user_id`. Use UTC in storage and localize for display. Never store real bank account numbers.

## Core tables

### users
`id UUID PK`, `display_name`, optional `email`, `locale DEFAULT 'en-IN'`, `timezone DEFAULT 'Asia/Kolkata'`, `default_currency DEFAULT 'INR'`, timestamps.

### demo_profiles
`id`, `user_id FK`, `persona_key`, `is_synthetic BOOLEAN NOT NULL`, `profile_label`, `created_at`. Must be explicitly synthetic.

### accounts
`id`, `user_id`, optional `demo_profile_id`, `display_name`, `account_type` (checking/savings/credit_card/cash/other), `currency`, `is_synthetic`, timestamps. Use fictional aliases only.

### import_batches
`id`, `user_id`, optional `account_id`, `source_type` (csv/pdf_text/pdf_ocr/sms_text/demo_seed), `original_filename`, private `storage_key`, `status` (uploaded/queued/processing/review_required/confirmed/completed/failed), row/accepted/rejected counts, safe `error_code`, created/completed timestamps.

### transactions
`id`, `user_id`, `account_id`, optional `import_batch_id`, `transaction_date`, optional `posted_date`, original and normalized descriptions, optional `merchant_id`, positive `amount NUMERIC`, `currency`, `direction` (debit/credit), `transaction_type` (expense/income/transfer/refund/fee/adjustment/unknown), optional category/subcategory IDs, categorization method/confidence, review status, duplicate fingerprint, excluded flag and timestamps.

### merchants
`id`, `canonical_name`, optional category hint/description, `is_fictional_demo`, created timestamp.

### merchant_aliases
`id`, `merchant_id`, `alias_pattern`, `match_type` (exact/normalized/limited_regex/fuzzy_reference), priority, active flag, timestamp. Do not permit unrestricted user regex.

### categories
`id`, optional parent category, name, category type (income/expense/transfer/neutral), system flag and sort order.

### categorization_rules
`id`, `user_id`, `scope_type` (exact_merchant/merchant_alias/description_contains/merchant_and_context), `scope_value JSONB`, `category_id`, priority, active, optional source transaction, timestamps.

### transaction_corrections
`id`, `user_id`, `transaction_id`, `field_name`, old/new values as JSONB, optional rule ID, created time and optional reverted time.

### recurring_commitments
`id`, `user_id`, optional merchant, display name, cadence, optional estimated cadence days, typical/min/max amounts, currency, confidence, status, last observed date, optional next expected date, evidence JSONB and timestamps.

### recurring_observations
`id`, `commitment_id`, `transaction_id`, observed amount/date and timestamp.

### price_change_events
`id`, commitment ID, previous/new amounts, absolute/percentage change, detected time, evidence JSONB and status (possible/confirmed_by_user/dismissed).

### financial_facts
`id`, `user_id`, fact type (income/fixed_cost/savings_balance/emergency_target/other), label, amount, currency, source type (user_confirmed/transaction_inferred/scenario_assumption/system_calculated), effective_from/to, optional confidence and source reference JSONB, created time.

### profile_snapshots
`id`, `user_id`, snapshot date, period start/end, income/expense/net cash flow, fixed/variable cost estimates, data coverage JSONB, model version and created time.

### budgets
`id`, `user_id`, category ID, amount, currency, period type, effective_from/to and timestamps.

### goals
`id`, `user_id`, title, description, target amount, current saved amount, currency, target date, priority, contribution frequency, planned contribution, status and timestamps.

### scenarios
`id`, `user_id`, title, scenario type, input parameters JSONB, baseline result JSONB, scenario result JSONB, assumptions JSONB, calculation version and created time.

### nudges
`id`, `user_id`, type, title, message, severity, evidence JSONB, status, created time and optional snooze time.

### monthly_reviews
`id`, `user_id`, period start/end, report JSONB, data coverage JSONB, generated time. Unique user+period.

### coach_conversations / coach_messages
Store minimal conversation metadata and messages with retention controls. Reference profile/transaction facts rather than duplicating full statement content.

### audit_events
`id`, `user_id`, event type, entity type/id, safe metadata JSONB and created time. Never log secrets or full statement contents.

## Relationships
A user owns accounts, imports, transactions, facts, snapshots, goals, budgets, scenarios, nudges and reviews. An import has many transactions. A merchant has aliases and transactions. A recurring commitment has observations and price events. A transaction can be linked to an observation. All relationships require ownership checks.

## Indexes
- transactions `(user_id, transaction_date DESC)`;
- transactions `(user_id, category_id, transaction_date)`;
- transactions `(user_id, merchant_id, transaction_date)`;
- transactions `(user_id, duplicate_fingerprint)`;
- import batches `(user_id, created_at DESC)`;
- recurring `(user_id, status)`;
- facts `(user_id, fact_type, effective_from)`;
- goals `(user_id, status)`;
- nudges `(user_id, status, created_at DESC)`;
- monthly reviews `(user_id, period_start)` unique.

Do not make duplicate fingerprint globally unique: identical legitimate purchases can occur. Scope uniqueness to account/import logic.

## Integrity
Amounts are non-negative magnitudes; currency valid; date ranges valid; goal target positive; current saved amount non-negative; effective end cannot precede start. Do not add mixed currencies. Do not store aggregates as the only source of truth.

## Migrations and seed data
Create incremental migrations. Seed system categories and fictional personas through idempotent scripts. Never seed real personal data.
