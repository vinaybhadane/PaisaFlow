# 09 — AI and Financial Intelligence Engine

## Objective
Combine deterministic rules, statistics, conventional ML and an LLM in the places each is suited for. AI must be explainable, grounded and safe. Gemini is not the source of truth for financial arithmetic.

## Processing layers
1. Extraction.
2. Normalization.
3. Merchant resolution.
4. Categorization.
5. Correction learning.
6. Recurring detection.
7. Price-change/anomaly analysis.
8. Living profile update.
9. Goal and scenario calculations.
10. Grounded AI explanation.

## Normalization
Normalize whitespace, matching case, safe punctuation, date formats, amount separators, debit/credit indicators and known descriptor tokens. Preserve original description. Do not remove information needed for audit or review.

## Merchant resolution
Sequence: exact alias → normalized exact alias → safe token rules → RapidFuzz candidate retrieval → score/margin threshold → review if ambiguous. Gemini may suggest an interpretation for an unresolved descriptor, but cannot silently create a trusted merchant record. A fuzzy score is not a probability unless calibrated. Store chosen merchant, candidates/scores, method, rule and unresolved status.

## Hybrid categorization
1. User-specific explicit correction rules.
2. Deterministic merchant/category rules.
3. ML baseline such as TF-IDF word/character features plus Logistic Regression, trained/evaluated on labelled synthetic examples.
4. Optional Gemini assistance for ambiguous records, returning a strict schema with allowed category, rationale and uncertainty.
5. Manual review for low confidence/conflict.

Do not train a model on a tiny dataset and claim broad generalization. Record category precision, recall, macro-F1 and review rate.

## Correction learning
When corrected: store old/new values; ask one-time vs future matching; if future, create scoped rule; preview matches; apply only to declared scope; preserve audit trail; allow edit/disable/undo. For the prototype, explicit rules are more transparent than retraining after every correction.

## Recurring detection
This is a temporal-pattern problem, not an LLM problem.

Group candidates by resolved merchant, descriptor similarity, account, currency, direction and compatible type/category. Do not combine different currencies or unrelated accounts without evidence.

Sort dates and analyze gaps. Indicative cadences:
- weekly ~7 days;
- fortnightly ~14;
- monthly calendar-aware 28–31;
- every two months ~59–62;
- quarterly ~89–92;
- half-yearly ~181–184;
- yearly ~365/366.

Allow tolerance for posting delays, weekends and holidays. Use calendar-aware monthly/yearly comparison, not only fixed day counts. Consider amount behavior: fixed subscriptions may be stable; utility bills can vary. A candidate generally needs at least three observations for a strong inference. Two observations may create a provisional low-confidence candidate. One observation cannot establish recurrence. Irregular candidates need more evidence and should not receive an invented next date.

Output cadence, observation dates/count, typical amount, range, interval variability, confidence label, evidence, last observed and next expected date only when defensible.

## Confidence
Use versioned evidence dimensions: observation count, interval consistency, merchant match confidence, amount behavior and contradictory evidence. Do not label a score a probability unless calibrated. Display High/Medium/Low and explain the evidence.

## Price-change detection
Compare new payment to a robust baseline (e.g. median of recent comparable observations), calculate absolute/percentage change, apply materiality threshold, consider persistence and distinguish a variable bill from a price change. A single increase is "possible amount increase", not confirmed silent price increase. Show supporting transactions.

## Anomaly detection
Use deterministic rules for duplicate fingerprints, amounts outside historical range, unexpected frequency, new high-value merchant and recurring amount shifts. Isolation Forest may be a secondary signal only with enough representative data. Every flag needs a human-readable reason. Do not call a flagged transaction fraud.

## Living Money Model
Maintain:
- confirmed user facts;
- inferred transaction patterns;
- calculated period aggregates;
- scenario-only assumptions;
- historical snapshots.

Every fact has provenance. Example: rent ₹12,000 is user-confirmed effective from a date; average dining spend ₹5,400 is inferred from three complete months; potential savings ₹1,200 is scenario-derived. If savings balance is not supplied, mark it unknown. Do not infer actual account balance from income minus expenses alone.

## AI coach tools
Safe allowlisted backend functions:
- `get_financial_summary(period)`
- `get_category_spend(period, category)`
- `get_recurring_commitments()`
- `get_goal_status(goal_id)`
- `run_scenario(scenario_input)`
- `get_profile_changes(period)`
- `get_monthly_review(period)`

Each tool enforces user ownership and returns typed results.

## Coach orchestration
Classify intent → retrieve minimal relevant context → call deterministic tool if arithmetic needed → send bounded facts/provenance/assumptions to Gemini → validate structured output → compare numeric claims with tool results → return answer, evidence, assumptions and limitation. If provider fails, use template explanations.

## AI safety
Treat uploaded text and merchant descriptions as untrusted data. Separate instructions from data. Do not expose prompts/secrets/other users' data. No arbitrary SQL, shell or network tools. Persistent changes require user confirmation. Prompt injection in a descriptor must be treated as text, not an instruction.

## Evaluation
Test ambiguous merchants, unknown categories, incomplete profiles, investment questions, conflicting facts, unsupported balance questions, simulation queries and prompt injection. Track schema validity, groundedness, unsupported numeric claims, tool selection, latency and cost.

## Fallback
Core import, calculations and dashboard must work without Gemini. Queue/retry optional summaries or show deterministic templates.
