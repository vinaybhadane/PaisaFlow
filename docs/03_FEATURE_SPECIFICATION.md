# 03 — Detailed Feature Specification

## Priority
P0 = required for credible end-to-end prototype. P1 = differentiator after P0. P2 = optional.

## 1. Onboarding and demo mode (P0)
- Provide a clearly labelled synthetic demo mode.
- Allow selection of a fictional persona.
- Explain that all displayed financial records are generated.
- Collect only display preferences, currency and optional goal preferences.
- Never request bank credentials, UPI PIN, OTP, CVV or real account identifiers.
Acceptance: a new user reaches a useful dashboard without supplying real financial information.

## 2. Statement ingestion (P0)
Formats: CSV, text PDF, pasted synthetic transaction notification; scanned PDF OCR is optional.
Flow: choose format → upload/paste → validate extension and actual content → create import batch → parse asynchronously → normalize → show preview → user accepts/excludes rows → commit idempotently → refresh aggregates.
Preview fields: date, description, debit, credit, currency, proposed category, confidence, warning and include/exclude.
Handle unsupported/encrypted/empty/oversized files, ambiguous dates, amount parse failures, malformed rows, duplicates and parser failures.

## 3. Transaction normalization (P0)
Canonical fields: ID, user, synthetic account, import batch, transaction date, posted date, ingestion time, original/normalized description, merchant, positive decimal amount, currency, direction, type, category, subcategory, method, confidence, review status and duplicate fingerprint.
Use positive magnitude plus separate direction/type.

## 4. Merchant resolution and categorization (P0)
Resolve exact aliases first, then normalized aliases, safe token rules and fuzzy matching. Ambiguous candidates go to review. Preserve original descriptor. Categories include income, housing, utilities, food, transport, health, shopping, education, entertainment/subscriptions, financial obligations, transfers, refunds and other/review.
Categorization hierarchy: user-specific rule → deterministic merchant rule → ML classifier → optional LLM assistance → manual review. Store method, confidence and evidence.

## 5. Correction learning (P0)
When user changes category/type:
- save correction history;
- ask whether it applies to this transaction only or future matching records;
- create scoped rule if user agrees;
- preview affected matches;
- do not silently rewrite historical records;
- allow rule edit, disable and undo.

## 6. Recurring intelligence (P0)
Detect weekly, fortnightly, monthly, every-two-months, quarterly, half-yearly, yearly and custom/irregular cadence. Handle fixed and variable amounts. Show merchant, cadence, observations, typical/range amount, confidence, evidence, last observed and expected next date only if defensible. Use "likely recurring" rather than claiming a contractual mandate.

## 7. Amount-change alerts (P0)
Compare new payment to historical comparable baseline. Show prior typical amount, new amount, absolute and percentage change, dates and evidence. A one-off variable bill is not automatically a price increase. Use "possible amount increase" until persistence or user confirmation supports stronger wording.

## 8. Living financial profile (P0)
Maintain effective-dated income, fixed costs, variable spending baselines, recurring commitments, user-supplied savings, emergency target, budgets and goals. Each fact includes source type, effective date, update time, confidence if inferred and supporting reference. Preserve history when values change.

## 9. Budgets (P1)
Monthly category budgets, actual spend, remaining amount, utilization, period and effective dates. Exclude transfers and handle refunds according to financial logic. Explain user-defined versus suggested budgets.

## 10. Goals (P0)
Fields: title, target amount, current saved amount, currency, target date, priority, contribution frequency, planned contribution and status. Show progress, required contribution, estimated completion and assumptions. Do not imply money is held in a real separate account.

## 11. What-if simulation (P0)
Templates: category reduction %, fixed reduction, rent increase, income change, one-time expense, hypothetical recurring commitment addition/removal and savings contribution change. Show baseline, scenario, difference, goal impact, assumptions and uncertainty. Scenario must never mutate actual transaction history.

## 12. AI coach (P0)
Ground responses in profile, transactions aggregates, recurring commitments, budgets, goals and calculation results. The coach cannot invent balances, guarantee forecasts, recommend securities, execute payments or claim a persistent change without backend confirmation. Use confirmation previews for supported profile changes.

## 13. Nudges (P1)
Each nudge contains trigger, supporting values, severity, suggested action, dismiss/snooze state and timestamp. Example: category budget 85% used with 10 days left. Avoid shame and alert spam.

## 14. Monthly review (P0)
Include month overview, income/expense/net cash flow, category breakdown, budget performance, recurring changes, month comparison, goal progress, one-off events, data coverage and evidence-backed suggestions.

## 15. Settings and data control (P0)
Profile, locale, currency, import history, correction rules, notification preferences, privacy explanation, AI status, demo reset, export and delete demo data.

## 16. Every feature's completion checklist
Requirements implemented; input validation; authorization; loading/empty/error/success UI; tests; provenance/audit where needed; accessibility; docs updated.
