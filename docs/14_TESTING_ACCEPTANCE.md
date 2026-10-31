# 14 — Testing Strategy and Acceptance Criteria

## Quality principle
A page rendering is not proof a feature works. Verify correctness, usability, safety and grounded AI behavior.

## Test layers
### Unit
Parsers, normalization, merchant matching, categorization rules, recurring intervals, confidence, formulas, scenario calculations and effective-date profile logic.

### Integration
API/database, import flow, correction-rule application, recurring persistence, goal CRUD, monthly review generation and coach retrieval/validation.

### End-to-end
Landing CTA, demo onboarding, CSV import, category correction, goal creation, simulation, monthly review and demo reset.

### AI evaluation
Grounded answers, correct tool selection, valid schema, no invented balances, safe investment boundary, prompt-injection resistance and numeric consistency.

## Required financial cases
1. Income/expense totals reconcile.
2. Transfers excluded.
3. Refund not ordinary income.
4. Duplicate import does not duplicate transaction.
5. Mixed currency totals separated/rejected.
6. Zero income does not divide by zero.
7. Invalid amounts rejected.
8. Partial coverage disclosed.
9. Goal reached → zero contribution.
10. Past target date → overdue, no negative division.
11. Category reduction arithmetic exact.
12. Rent increase affects future scenario only.
13. Scenario does not mutate transaction history.
14. Annual recurring equivalent labelled estimate.

## Required intelligence cases
Categorization: exact alias, normalized alias, ambiguous descriptor, user rule priority, disabled rule, low confidence review.
Recurrence: monthly fixed, monthly variable utility, weekly, quarterly, annual, date jitter, missing occurrence, alias change, insufficient history and one-off non-recurring payment.
Price change: stable amount, one-off variable bill, persistent increase, rounding noise, insufficient history and decrease.

## Prototype target thresholds
These are targets to measure, not claims:
- 100% pass for financial calculation unit tests.
- 100% pass for import idempotency tests.
- 100% pass for critical authorization tests.
- Target categorization precision >=90% on supported labelled synthetic categories.
- Report recurring precision/recall and false positives by cadence.
- No unsupported numeric claims in AI evaluation suite.
- All P0 user journeys pass.

Never claim synthetic test performance proves real-world performance.

## UX acceptance
Landing CTA and navigation work; all links lead somewhere; demo values labelled; dashboard uses API or explicit fixture; loading/empty/error states; mobile layout; labels and validation; keyboard focus; chart text summaries; no dead controls; confirmed/inferred/scenario values distinguished.

## Security acceptance
No secrets; no real data; file validation; cross-user access tests; prompt-injection tests; no raw statement logs; isolated demo reset; HTTPS in deployment.

## Performance
Measure landing load, dashboard API, import duration by file size, recurrence analysis, coach latency and report generation. Set budgets after measuring actual deployment; do not invent metrics.

## Regression process
For every bug: add failing test, fix, rerun relevant suite, run full P0 suite before demo and record meaningful findings in `EXPERIMENT_LOG.md`.

## Demo checklist
Reset works; synthetic label visible; fixtures available; no exposed API key; Gemini fallback works; charts reconcile; correction learning demonstrable; recurring evidence visible; scenario reproducible; monthly coverage note present; desktop/mobile polished.
