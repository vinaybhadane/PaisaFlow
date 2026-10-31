# 07 — System Architecture

## Architecture style
Use a **modular monolith with a background worker**. This keeps domain boundaries clean without microservice operations. Deploy frontend, API and worker as separate processes; PostgreSQL and Redis are supporting services.

## High-level architecture
```text
Browser
  |
  v
Next.js Web App
  | HTTPS / JSON
  v
FastAPI API
  |------------------------------|
  v                              v
Domain Services               AI Coach Service
  |                              |
  |                              v
  |                          Gemini API
  |
  |---- PostgreSQL (+ pgvector)
  |---- Azure Blob Storage
  |---- Redis Queue
             |
             v
        Celery Worker
        - parse files
        - normalize records
        - categorize
        - detect recurrence
        - detect amount changes
        - generate reports
             |
             v
        PostgreSQL
```

## Frontend responsibilities
Public landing page, onboarding, dashboard, import wizard, review screen, transaction correction, recurring commitments, budgets, goals, simulator, AI coach, monthly reports and settings. Frontend must not be authoritative for financial totals. A slider may show a temporary preview, but backend results are authoritative.

## Backend modules
```text
backend/app/
  api/v1/routes/
  core/
  db/
  models/
  schemas/
  repositories/
  services/
    import_service.py
    transaction_service.py
    merchant_service.py
    categorization_service.py
    recurring_service.py
    profile_service.py
    budget_service.py
    goal_service.py
    simulation_service.py
    nudge_service.py
    report_service.py
    coach_service.py
  intelligence/
    normalization/
    merchant_resolution/
    categorization/
    recurrence/
    anomaly/
    forecasting/
    scoring/
  workers/
  prompts/
```

## Import processing sequence
1. Authenticate/resolve demo profile.
2. Validate upload metadata and actual content.
3. Create import batch in `uploaded` state.
4. Store file privately.
5. Enqueue job.
6. Worker parses source and normalizes candidate rows.
7. Validate dates, amounts and currency.
8. Calculate duplicate fingerprints.
9. Resolve merchant and propose category.
10. Save preview rows as pending review.
11. User confirms accepted rows.
12. Commit idempotently in a database transaction.
13. Refresh affected profile aggregates and recurrence analysis.
14. Mark import completed and return counts.

Do not auto-import ambiguous rows without a review step.

## Living model update sequence
Trigger on confirmed import, correction, recurring review, income/fixed-cost edit, goal change or budget change. Validate ownership; persist source fact/correction; recompute affected aggregates from source facts; create profile snapshot/version; record provenance; invalidate caches; generate eligible nudges. Prefer recomputation to untraceable delta accumulation.

## AI coach sequence
Validate question → retrieve minimal user-scoped context → call deterministic financial tools when arithmetic is needed → construct bounded prompt with facts and provenance → call Gemini → validate output → verify numeric claims against tool outputs → return answer with supporting facts and limitations. If Gemini fails, show deterministic results with a templated explanation.

## Data boundaries
- PostgreSQL: canonical financial and profile data.
- Blob Storage: original synthetic files and generated reports.
- Redis: ephemeral jobs/cache, never sole source of financial facts.
- Gemini: minimal context needed; avoid raw statement transmission.
- Browser: no secrets and no direct database access.

## Reliability
Jobs must be retry-safe and idempotent. Import confirmation uses stable IDs/idempotency keys. Database transaction protects final commit. Failed jobs expose safe error codes and retry state. Use bounded retries.

## Observability
Track request ID, demo/user ID, import batch ID, worker job ID, stage, duration, error code, model and prompt version. Do not log raw transaction descriptions or statement content.

## Scalability
Paginate transactions, index query paths, process large files asynchronously, cache only recomputable data and keep modules separable. Microservices are not needed for the hackathon.
