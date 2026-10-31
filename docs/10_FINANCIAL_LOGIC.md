# 10 — Financial Logic, Formulas and Simulation Rules

## Authority
This is the authoritative arithmetic specification. Implement formulas in tested backend services. LLMs may explain results but must never calculate authoritative values.

## Money representation
Use Python `Decimal` and PostgreSQL `NUMERIC`; store positive amount magnitude plus direction/type. Every amount has ISO currency. Do not sum currencies without explicit exchange-rate record, source, timestamp and policy. Multi-currency conversion is out of initial scope. Round only for display or defined business boundaries.

## Transaction types
Income, expense, transfer, refund, fee, adjustment, unknown. Own-account transfers are excluded from consolidated income/expense. Credit-card bill payments must not double count purchases already included. Refunds should be linked to original purchase and reduce the relevant category where possible; otherwise display separately and disclose gross/net treatment.

## Periods
Use `Asia/Kolkata` calendar months in user-facing reports. Store timestamps UTC. March period is local March 1 through March 31 inclusive. Do not mix transaction and posting dates without disclosure.

## Totals
`income_total = sum(amount where direction=credit and type=income)`  
`expense_total = sum(amount where direction=debit and type=expense)`  
`net_cash_flow = eligible_income_total - eligible_expense_total`

Exclude transfers, duplicates, excluded rows and unresolved records unless shown separately as unclassified. Refund policy must be consistent.

Net cash flow is not necessarily account balance change or savings balance.

## Savings rate
When income is positive and coverage is sufficient:
`cash_flow_savings_rate = (income_total - expense_total) / income_total * 100`
Label as estimated/cash-flow savings rate. Do not display when income is zero or missing.

## Budget
`category_spend = sum(eligible net expense for category and period)`  
`budget_utilization = category_spend / budget_amount * 100`  
`budget_remaining = budget_amount - category_spend`
If budget is absent/zero, utilization is undefined; never divide by zero.

## Recurring monthly equivalents
- monthly: amount;
- weekly: amount × 52 / 12;
- fortnightly: amount × 26 / 12;
- quarterly: amount / 3;
- half-yearly: amount / 6;
- yearly: amount / 12.

These are planning equivalents, not actual monthly charges. Irregular patterns should not be annualized without a defensible observation window and explicit uncertainty.

## Goal contribution
For target `T`, current saved `S`, remaining periods `n`:
`remaining = max(T - S, 0)`  
`required_contribution_per_period = remaining / n`
Use calendar-aware period counting. If goal reached, contribution is zero. If target date passed, mark overdue; do not divide by negative periods. Base model assumes no interest/returns.

## Scenario: percentage category reduction
Baseline category spend `B`; reduction percentage `p` from 0 to 100:
`new_spend = B × (1 - p/100)`  
`monthly_improvement = B - new_spend`  
`annualized_improvement = monthly_improvement × 12`
Annualization assumes behavior persists for 12 months and baseline is stable. Example: ₹6,000 dining reduced by 30% → ₹4,200 new spend, ₹1,800 monthly improvement, ₹21,600 annualized.

## Scenario: fixed reduction
`new_spend = max(B - reduction_amount, 0)`  
`monthly_improvement = B - new_spend`
Reject negative reduction and explain if requested reduction exceeds baseline.

## Scenario: rent increase
For current rent `R`, increase `I`:
`new_rent = R + I`  
`new_monthly_surplus = baseline_monthly_surplus - I`
For percentage `p`, `I = R × p/100`. Apply from selected effective date in future scenario; do not rewrite history.

## Scenario: income change
`new_income = current_income + change_amount`  
`new_surplus = new_income - planned_expenses`
For variable income, show user-selected conservative/baseline/optimistic assumptions. Do not invent distributions.

## Scenario: recurring commitment removal
Hypothetical future scenario only. Monthly equivalent savings equals the commitment's monthly planning equivalent. Do not mark cancelled or alter transaction history. Explain actual cancellation is not performed.

## Goal projection
`projected_amount = current_saved_amount + contribution_per_period × periods`  
`periods_needed = ceil(remaining / contribution_per_period)`
If contribution is zero, completion is unknown/unreachable under the scenario. State no interest/return assumption.

## Monte Carlo (optional P1)
Use only with sufficient data or explicit user-supplied uncertainty assumptions. Output median and percentile ranges, and probability of goal achievement under those assumptions. Never imply guarantee. Deterministic scenarios take priority for MVP.

## Emergency fund
If user supplies current amount and target:
`progress = current_amount / target_amount × 100`
If target is defined by essential expense months:
`target = essential_monthly_expenses × selected_month_count`
Do not prescribe a universal target; user selects it or a default is clearly educational.

## Coverage and confidence
Each report includes days covered, transactions, accounts included, missing periods, excluded and unresolved rows. Do not compare incomplete months as equivalent.

## Rounding/reconciliation
Keep full decimal precision internally; round for display. Calculate percentages from unrounded totals. Charts must reconcile to displayed totals except documented rounding. Unit-test boundary conditions.

## Forbidden behavior
No guaranteed returns, securities recommendations, personalized investment allocation, claim that cash flow equals bank balance, automatic movement of money, credit decisions or hidden assumptions.
