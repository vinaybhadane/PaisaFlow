# 12 — Synthetic Data Specification

## Purpose
Generate realistic but entirely fictional records to demonstrate requirements and edge cases. Never copy a real person's bank statement.

## Personas
### Asha Mehta — salaried professional
Fictional; INR; monthly income around ₹48,000; rent, utilities, food, transport, subscriptions; emergency-fund goal; six or more months of history.

### Kabir Shah — freelancer
Fictional; variable client receipts; irregular income; variable work expenses; utilities and subscriptions; laptop goal; nine or more months of history.

These are synthetic identities, not references to real people.

## Dataset volume
Recommended: 2 personas, 2–3 fictional accounts each, 6–12 months, 150–400 transactions per persona, 15–30 merchant identities, 10–15 recurring patterns and at least 10 deliberate edge cases. Use fixed random seeds for reproducibility.

## Fictional merchants and aliases
Examples:
- FRESHMART RETAIL / FRESH MART POS
- CITYRIDE MOBILITY / CITYRIDE APP
- STREAMBOX MEDIA / STREAMBOX SUB
- CLOUDNEST STORAGE / CLDNEST BILL
- NORTHSTAR UTILITIES / NSTAR ELEC
- METRO HOME RENT / MHR RENT

Use fictional names where possible. If recognizable real brand names appear in an illustrative example, label the record synthetic and do not imply affiliation.

## Transaction fixture fields
Date, optional posted date, descriptor, debit/credit amount, currency, fictional account alias, optional reference, expected category, expected type and edge-case tag. Never include actual account numbers, addresses, phone numbers or identifiers.

## Required scenarios
A. Monthly salary with slight date jitter.  
B. Monthly rent with mid-year increase.  
C. Variable electricity bill on monthly cadence.  
D. Subscription amount changes from ₹149 to ₹179 after several months.  
E. Annual membership-like fictional charge.  
F. Quarterly service fee.  
G. Irregular freelance income.  
H. Refund that must not be treated as ordinary income.  
I. Paired own-account transfer excluded from spending/income.  
J. Same transaction imported twice; safely deduplicate.  
K. Different descriptors map to one merchant.  
L. Ambiguous descriptor remains unresolved for review.  
M. Deliberately incorrect category demonstrates correction loop.  
N. Trial-to-paid example with a separate explicit synthetic trial-start event; statement alone cannot prove a free trial.  
O. Unusual one-off amount flagged for review, not called fraud.  
P. Malformed date/amount row in parser tests, not accepted data.

## File fixtures
Generate clean CSV, alternate-column CSV, ambiguous-date CSV, text PDF, optional scanned-style PDF if OCR tested, pasted notification text and malformed file. Add a header/footer/metadata label "Synthetic demo data — not a real bank statement."

## Generation rules
Use Faker and fixed seeds. Use explicit scenario configuration for known edge cases. Keep currency INR unless testing multi-currency separately. Generate plausible fictional amounts, not copied real histories. Store expected labels separately from input files.

## Evaluation ground truth
Separate file with row ID, canonical merchant, expected category/type, recurring group ID, cadence, price-change event, duplicate group and anomaly label. Never pass ground-truth labels to model during prediction.

## Reset
Idempotent reset clears only selected demo profile, regenerates fixed-seed records, preserves system categories, reports created records and never deletes another user's data.

## UI
Every demo profile, import and exported report must show "Synthetic data". Never present generated amounts as real financial facts or personalized investment advice.
