# 04 — User Journeys and Interaction Flows

## Experience goals
A new user should understand PaisaFlow quickly, reach a useful result and always know whether a value is synthetic, confirmed, inferred or a scenario assumption.

## 1. Landing page
Visit → understand hero promise → review features and workflow → inspect synthetic scenario preview → read privacy boundary → choose Explore Demo/Get Started → enter onboarding. Primary CTA must be visible above the fold and work on mobile.

## 2. First-time onboarding
Welcome → explain synthetic-only demo → choose sample profile (salary earner/freelancer) → load fictional profile → show guided dashboard checklist. Never ask for bank login or sensitive payment credentials.

## 3. Statement import
Transactions → Import → choose CSV/PDF/pasted text → explain synthetic-data requirement → select file → client progress → backend validation → queued processing → preview extracted rows → review uncertain rows → confirm accepted rows → deduplicate and persist → refresh dashboard/profile → show imported/skipped/flagged summary.
Failure paths: unsupported format, encrypted PDF, OCR unavailable, ambiguous dates, malformed amount, duplicate file, processing failure. Provide retry or manual mapping when safe.

## 4. Transaction correction
Open transaction → see original descriptor, merchant, proposed category, confidence and reason → choose category → choose one-time correction or future matching rule → preview rule matches → confirm → save correction and audit event → show confirmation → future matching transactions use rule. Provide undo/disable.

## 5. Recurring review
Open Recurring → inspect cadence, typical amount, observations, confidence and evidence → confirm/reject/needs review → confirmed item enters profile → amount change shows timeline. Do not label an inferred pattern a verified mandate.

## 6. Living profile
Open Money Profile → inspect income, fixed costs, variable spend, savings and goals → each value shows provenance → edit user-maintained fact with effective date → preserve prior version → update snapshot → show timeline change.

## 7. Goal creation
Create goal → enter name, target, current saved amount, date, priority and contribution plan → validate → calculate required contribution → display assumptions → confirm → show goal card and coach context.

## 8. What-if simulation
Open Simulator or ask coach → choose scenario → enter amount/percentage and period → show baseline inputs → calculate on backend → show before/after cash flow and goal impact → explain with AI → optionally save scenario. Saving must not modify actual transactions.

## 9. AI coach
Submit question → validate → retrieve relevant user-scoped facts → call deterministic tools if arithmetic is needed → send bounded context to Gemini → validate response → render facts, assumptions and limitations. If data is missing, ask a question or state the limitation. For persistent changes, preview and require confirmation.

## 10. Monthly review
Choose month → calculate from transactions and profile → display coverage warning → show cash flow, categories, budgets, recurring changes, goals and insights → drill into supporting transactions → export if implemented.

## 11. Empty states
- No transactions: "Import a synthetic statement to build your money picture."
- No recurring pattern: "More transaction history is needed to identify recurring commitments."
- No goals: "Create a goal to see how today's cash flow supports tomorrow's plans."
- No review: "A review appears when this period has transaction data."

## 12. Accessibility and responsive flow
All flows keyboard accessible. Inputs have labels and clear errors. Dialogs manage focus. Charts have text alternatives. Touch targets are usable. Tables adapt to mobile using cards or intentional horizontal scrolling.
