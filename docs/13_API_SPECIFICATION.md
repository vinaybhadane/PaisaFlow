# 13 — API Specification

## Conventions
Base `/api/v1`; HTTPS in deployment; JSON except multipart uploads; dates `YYYY-MM-DD`; timestamps ISO 8601; money values decimal strings (e.g. `"1250.00"`); currency ISO 4217, initially INR. Paginate lists. Enforce user/demo-profile ownership.

## Standard success
```json
{
  "data": {},
  "meta": {"request_id": "uuid", "generated_at": "2026-01-01T10:00:00Z"}
}
```
## Standard error
```json
{
  "error": {"code": "VALIDATION_ERROR", "message": "The amount must be greater than zero.", "details": []},
  "meta": {"request_id": "uuid"}
}
```
Never return stack traces or secrets.

## Health/config
- `GET /health`: service health only; no secrets.
- `GET /api/v1/config`: safe config such as supported currency, upload formats and feature flags.

## Demo profiles
- `GET /api/v1/demo/profiles`: fictional personas.
- `POST /api/v1/demo/profiles/{profile_id}/activate`: activate synthetic persona.
- `POST /api/v1/demo/reset`: reset only current user's selected profile; require explicit confirmation.

## Imports
- `POST /api/v1/imports`: multipart `file`, optional synthetic `account_id`, `source_type`, optional `demo_profile_id`; returns import ID/status.
- `GET /api/v1/imports/{import_id}`: status and summary.
- `GET /api/v1/imports/{import_id}/preview`: extracted rows, confidence and warnings.
- `POST /api/v1/imports/{import_id}/confirm`: accepted/excluded row IDs; validate ownership and idempotently commit.
- `POST /api/v1/imports/{import_id}/retry`: retry safe failed/reviewable job.

## Transactions
- `GET /api/v1/transactions`: filters `from`, `to`, `category_id`, `transaction_type`, `merchant_id`, `review_status`, `page`, `page_size`, `search`.
- `GET /api/v1/transactions/{transaction_id}`: detail and provenance.
- `PATCH /api/v1/transactions/{transaction_id}`: safe editable fields; record correction history.
- `POST /api/v1/transactions/{transaction_id}/correction-rule`: create scoped future rule, optionally preview.
- `GET /api/v1/categorization-rules`: list rules.
- `PATCH /api/v1/categorization-rules/{rule_id}`: edit/enable/disable.
- `POST /api/v1/categorization-rules/{rule_id}/undo`: deactivate/revert according to audit policy.

## Summary/profile
- `GET /api/v1/financial-summary?period_start=&period_end=`: income, expenses, refunds, excluded transfers, net cash flow, savings-rate estimate and data coverage.
- `GET /api/v1/profile`: current facts with provenance.
- `GET /api/v1/profile/history`: snapshots and changes.
- `POST /api/v1/profile/facts`: user-confirmed fact.
- `PATCH /api/v1/profile/facts/{fact_id}`: effective-dated update preserving history.

## Recurring
- `GET /api/v1/recurring`: candidates with cadence, amounts, confidence, evidence and status.
- `POST /api/v1/recurring/{commitment_id}/review`: confirmed/rejected/needs_review.
- `GET /api/v1/recurring/{commitment_id}/history`: observations and price events.

## Budgets
- `GET /api/v1/budgets`
- `POST /api/v1/budgets`
- `PATCH /api/v1/budgets/{budget_id}`
- `DELETE /api/v1/budgets/{budget_id}`

Preserve effective dates when appropriate.

## Goals
- `GET /api/v1/goals`
- `POST /api/v1/goals`
- `GET /api/v1/goals/{goal_id}`
- `PATCH /api/v1/goals/{goal_id}`
- `DELETE /api/v1/goals/{goal_id}`

Goal creation returns deterministic contribution estimate and assumptions.

## Simulations
- `POST /api/v1/simulations/run`: accepts scenario type, validated inputs, date range and optional goal; returns baseline, scenario, delta, assumptions and calculation version.
- `POST /api/v1/simulations`: save result.
- `GET /api/v1/simulations`: list.
- `DELETE /api/v1/simulations/{id}`: delete.

Example input:
```json
{
  "scenario_type": "reduce_category_percentage",
  "category_id": "uuid",
  "reduction_percentage": "30",
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "goal_id": "uuid"
}
```

## Nudges/reviews
- `GET /api/v1/nudges`
- `POST /api/v1/nudges/{id}/dismiss`
- `POST /api/v1/nudges/{id}/snooze`
- `GET /api/v1/reviews/{year}/{month}`
- `POST /api/v1/reviews/{year}/{month}/generate` (idempotent per user/period).

## AI coach
- `POST /api/v1/coach/messages`: conversation ID and message; response contains answer, grounded facts, calculation references, assumptions, warnings and optional action proposal.
- `POST /api/v1/coach/actions/{action_id}/confirm`: only supported low-risk profile actions. No payment/cancellation action.

## Validation and limits
Set upload, row, pagination, message and date-range limits. Validate currency and categories. Reject cross-user IDs. Rate-limit AI/import. Use idempotency keys for retryable mutations. Return 404 for inaccessible user-owned records.

## OpenAPI
FastAPI-generated OpenAPI is executable contract. Keep docs synchronized with route schemas and tests. Do not add undocumented endpoints.
