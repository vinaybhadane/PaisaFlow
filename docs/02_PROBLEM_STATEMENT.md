# 02 — Hackathon Problem Statement and Interpretation

## Challenge
Build a Personal Finance Coach with a Living Money Model. Typical budgeting apps categorize transactions and stop. They do not adequately understand a person's goals or adapt as life changes.

## Required capabilities

### A. Messy financial data ingestion
Accept synthetic PDF statements, CSV exports and transaction SMS-like text. Identify format, parse rows, normalize date/description/amount/debit-credit/currency, flag uncertain rows, preview before import and prevent duplicate imports.

### B. Automatic categorization
Each transaction needs normalized merchant/description, category/subcategory, transaction type, method, confidence, evidence and review status. Use deterministic rules first, ML for suitable cases and LLM assistance only for ambiguity. User corrections are mandatory.

### C. Correction loop
Save old/new values, ask whether the correction applies to future matching transactions, create a scoped rule, preview matches, support undo/disable and do not silently rewrite history.

### D. Recurring payments
Detect weekly, fortnightly, monthly, quarterly, annual and irregular patterns; fixed and variable amounts; merchant aliases; price changes and missed periods. Treat recurrence as an inference, not proof of a contractual mandate.

### E. Persistent financial profile
Maintain income streams, fixed costs, variable spending baselines, recurring commitments, user-supplied savings balance, emergency target, budgets and goals. Preserve effective-dated history. Distinguish user-confirmed facts from inferred values.

### F. Goals and what-if simulation
Goal inputs: name, target amount, current saved amount, target date, priority and contribution plan. Scenarios: reduce dining, rent increase, income change, one-time expense, remove/add a hypothetical recurring commitment. Show baseline, changed inputs, result, assumptions and limitations.

### G. Nudges
Evidence-backed, timely, dismissible, snoozable and non-judgmental. Avoid repetitive alerts.

### H. Monthly review
Show income, expenses, net cash flow, category spending, budget variance, recurring commitments, month-over-month changes, goal progress, notable one-off expenses and evidence-backed suggestions. Disclose incomplete data coverage.

## Core questions PaisaFlow should answer
- What happened to my money?
- Which transactions appear recurring?
- What changed since last month?
- What can I allocate to a goal under stated assumptions?
- What happens if rent rises?
- Why did I receive this nudge?
- Which facts are confirmed, inferred or estimated?

## Hackathon constraints
Synthetic data only. No real bank connectivity, real payment execution, real cancellation or specific securities recommendations.

## Minimum viable demo
1. Load/upload synthetic statement.
2. Extract and normalize transactions.
3. Categorize transactions.
4. Correct a category and show future rule learning.
5. Detect recurring pattern and amount change.
6. Update financial profile.
7. Create savings goal.
8. Run deterministic what-if scenario.
9. Explain result with AI grounded in tool output.
10. Generate monthly review.

## Difficult demonstration cases
Merchant descriptor alias; recurring payment with amount/date variation; refund; own-account transfer; duplicate import; rent increase; salary change; ambiguous merchant; one-off unusual payment.

## Judging alignment
- Prototype quality and UX (20%): complete responsive landing page and working app.
- AI integration (20%): grounded coach, correction learning and contextual model.
- Problem understanding (15%): correct ingestion, categorization, recurrence, profile and goals.
- LinkedIn content and engagement (15%): authentic progress/demo/educational content.
- Innovation and creativity (10%): living model, explainable simulation and adaptive context.

These listed weights may not be the entire rubric. Use the event's official complete rubric as final authority.

## Evidence for judges
Show correction before/after, recurrence evidence, profile timeline, exact what-if arithmetic, grounded AI response, monthly review and synthetic-data/privacy labels.
