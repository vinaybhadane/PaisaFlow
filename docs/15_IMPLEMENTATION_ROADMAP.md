# 15 — Implementation Roadmap

## Delivery strategy
Build complete vertical slices. Do not generate every screen before backend behavior exists.

## Phase 0 — Inspect and plan
Read docs, inspect repository, identify gaps, verify tool versions, confirm environment and produce task plan. Exit: no unresolved architecture conflicts; `.env.example` placeholders created.

## Phase 1 — Foundation
Initialize Next.js strict TypeScript, FastAPI, PostgreSQL, Alembic, Docker Compose, health endpoint, lint/type/test commands and reusable app shell. Exit: frontend/API run; migration works; CI checks pass.

## Phase 2 — Premium landing page
Implement responsive navigation, hero, synthetic dashboard preview, problem section, feature grid, how-it-works, interactive illustrative what-if, Living Model section, privacy, FAQ and footer. Verify CTA, links, accessibility and mobile. Exit: no dead controls; responsive QA complete.

## Phase 3 — Synthetic data and ingestion
Build fixed-seed persona generator; CSV parser; text PDF parser; SMS parser; optional OCR; normalization; import preview/confirmation; duplicate detection. Exit: CSV end-to-end import, uncertain row review and malformed input handling work.

## Phase 4 — Transaction intelligence
Seed taxonomy and merchant aliases; exact/fuzzy resolution; baseline ML if labelled data supports it; confidence/review; correction persistence; future rules; undo. Exit: correction affects future match and ambiguous records remain reviewable.

## Phase 5 — Recurring and anomaly intelligence
Candidate grouping, cadence detection, variable amounts, evidence/confidence, price-change detection and UI. Exit: synthetic patterns detected; one-off not falsely marked recurring; evidence visible.

## Phase 6 — Living Money Model
Effective-dated facts, profile snapshots, income/fixed-cost baselines, provenance labels, timeline and update triggers. Exit: new rent/income updates current model while history remains.

## Phase 7 — Goals and simulations
Goal CRUD, contribution calculation, budgets, scenario validation, deterministic calculations, persistence and charts. Exit: at least three scenarios; tests reconcile; actual history unchanged.

## Phase 8 — AI coach and nudges
Gemini integration, prompt versioning, bounded context, deterministic tools, structured validation, financial safety boundaries, grounded UI, fallback and nudges. Exit: answers grounded; numeric claims match tools; missing data acknowledged; fallback works.

## Phase 9 — Monthly review and polish
Monthly report, comparisons, coverage note, empty/error/loading states, responsive/accessibility/performance review and demo reset. Exit: P0 acceptance suite passes.

## Phase 10 — Azure deployment
Check credit, region, pricing and quotas; containerize; provision only required resources; configure secrets/managed identity; deploy; migrate/seed; monitor; configure budget alerts and teardown plan. Exit: deployed user journey works without exposing secrets.

## Priority if time is short
1. Landing page and usable dashboard.
2. Synthetic CSV import.
3. Categorization and correction loop.
4. Recurring detection.
5. Living profile.
6. Deterministic simulation.
7. Grounded AI explanation.
8. Monthly review.
Defer OCR, advanced ML and Monte Carlo until P0 is reliable.

## Antigravity task protocol
Before each phase list files to change, implement one slice, run tests, update `PROGRESS.md`, record decisions and do not pass a failed critical acceptance gate silently.
