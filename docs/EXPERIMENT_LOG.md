# PaisaFlow — Experiment Log

Record experiments with measured results only. Do not invent results.

## Entry template
### EXP-XXX — [Title]
- Date:
- Owner:
- Hypothesis:
- Component:
- Dataset version and size:
- Method:
- Baseline:
- Variant:
- Metrics:
- Results:
- Failure cases:
- Decision (keep/modify/reject/repeat):
- Follow-up:

## Metrics
Categorization: accuracy, precision/recall per category, macro-F1, confusion matrix, review rate.  
Merchant matching: exact match, top-1 accuracy, false-match rate, unresolved rate.  
Recurring: precision, recall, false positives/negatives, cadence error, results by cadence/amount variability.  
AI coach: schema validity, groundedness, unsupported numeric claims, tool selection, latency and fallback rate.  
UX: task completion, import time, correction completion and clarity feedback.

## Initial experiments
1. Exact aliases vs RapidFuzz-assisted merchant matching.
2. Rule-only vs hybrid categorization.
3. Monthly cadence with date jitter.
4. Variable utility bill vs fixed subscription.
5. Price-change threshold vs one-off variable charges.
6. AI numeric claims vs deterministic tool results.
7. Prompt injection embedded in transaction descriptions.
8. Landing CTA and onboarding on mobile.

No results have been recorded yet. Add results only after running the experiments.
