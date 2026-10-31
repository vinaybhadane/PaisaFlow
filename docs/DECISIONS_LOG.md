# PaisaFlow — Architecture and Product Decisions Log

## Decision template
### ADR-XXX — Title
- Status: Proposed / Accepted / Superseded
- Date:
- Context:
- Decision:
- Alternatives:
- Consequences:
- Related docs:

## ADR-001 — Synthetic data only
- Status: Accepted
- Context: Hackathon requires synthetic financial data.
- Decision: All demo records are fictional; no real bank or inbox integrations.
- Consequence: Future extensibility is allowed, but real data is prohibited in the hackathon build.

## ADR-002 — Deterministic financial calculations
- Status: Accepted
- Context: LLM arithmetic is not sufficiently reliable as source of truth.
- Decision: Backend services calculate all totals and scenarios with Decimal.
- Consequence: Gemini explains validated outputs.

## ADR-003 — Modular monolith
- Status: Accepted
- Context: Hackathon needs speed and reliability.
- Decision: Modular FastAPI backend plus separate worker, not microservices.
- Consequence: Simpler deployment and clear domain boundaries.

## ADR-004 — PostgreSQL source of truth
- Status: Accepted
- Context: Financial records require relational integrity and history.
- Decision: PostgreSQL stores canonical records; pgvector only for optional contextual retrieval.
- Consequence: NUMERIC, foreign keys, migrations and indexes required.

## ADR-005 — Azure cloud direction
- Status: Accepted
- Context: Project owner has Azure for Students.
- Decision: Prefer Azure where current credit, cost and availability permit.
- Consequence: Verify all service pricing before provisioning.

## ADR-006 — Gemini for language assistance
- Status: Accepted
- Context: Conversational coaching is useful, but numeric correctness is critical.
- Decision: Gemini explains and structures language; backend tools supply financial facts and arithmetic.
- Consequence: Validate model outputs and numeric claims.

## ADR-007 — UI library integration: SmoothUI and Unlumen UI
- Status: Accepted
- Date: 2026-10-31
- Context: PaisaFlow requires polished interactive CTA controls and contextual tooltips (for confidence, synthetic disclosures, and provenance) integrated into Next.js 15 App Router with Tailwind CSS v4 and Motion.
- Decision: Install `smooth-button` via SmoothUI CLI and `floating-tooltip` via Unlumen UI (shadcn registry) directly as source components in `frontend/components/`. Configure path aliases and unified `@/lib/utils` `cn` helper.
- Consequences: Retains complete source control, strict TypeScript compliance, zero hydration issues, and clean Next.js production builds.
- Related docs: `docs/17_FRONTEND_UI_LIBRARIES.md`, `frontend/README.md`.

## ADR-008 — Async PostgreSQL, Alembic Offline DDL, and In-Memory Unit Test Isolation
- Status: Accepted
- Date: 2026-10-31
- Context: Backend requires strict PostgreSQL types (UUID, NUMERIC(18, 2), JSONB, compound indexes) with SQLAlchemy 2 asyncpg and Alembic migrations, while allowing continuous testing and verification in environments where a live PostgreSQL daemon or Docker service may not yet be running.
- Decision: Use asyncpg engine for runtime and Alembic migrations targeting PostgreSQL. Verify migrations using Alembic offline transactional SQL generation (`alembic upgrade head --sql`). Structure models with generic JSON types having JSONB PostgreSQL variants, allowing isolated in-memory unit testing for seeding, idempotency, and reset validation without substituting SQLite as the application architecture.
- Consequences: Preserves 100% PostgreSQL schema integrity for deployment while ensuring reliable CI/CD and developer testing.
- Related docs: `docs/08_DATABASE_SCHEMA.md`, `docs/14_TESTING_ACCEPTANCE.md`.

Add new ADRs below. Supersede accepted decisions explicitly rather than silently rewriting them.
