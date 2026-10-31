# 06 — Approved Technology Stack and Rationale

## Selection criteria
Choose technologies for financial correctness, Python analytics capability, maintainability, hackathon delivery speed, polished UX, Azure compatibility, testability and manageable operating cost. Do not choose tools based on a developer's previous project history. Add no dependency without a defined requirement.

## Approved stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | Next.js (React + TypeScript) | Strong routing, rendering and production UI ecosystem |
| Styling | Tailwind CSS | Consistent responsive styling |
| Components | shadcn/ui + Radix primitives | Accessible customizable components |
| Charts | Apache ECharts | Rich financial charts and interactions |
| Server state | TanStack Query | Caching, refetching and mutation management |
| Local UI state | React state/Zustand | Ephemeral state only |
| Backend | Python + FastAPI | Mature data/ML ecosystem and typed APIs |
| Validation | Pydantic v2 | Strict request/response validation |
| Database | PostgreSQL | Relational integrity and financial queries |
| Vector extension | pgvector | Context retrieval without another database |
| ORM | SQLAlchemy 2.x | Database access and transactions |
| Migrations | Alembic | Versioned schema |
| Jobs | Celery | Asynchronous statement and report processing |
| Broker/cache | Redis | Job queue and short-lived cache |
| Data processing | Polars; Pandas where compatibility requires | Efficient transformations |
| PDF | PyMuPDF + pdfplumber | Text and table extraction |
| OCR | PaddleOCR (optional after CSV/text PDF) | Scanned statement extraction |
| Matching | RapidFuzz | Merchant alias resolution |
| Statistics | NumPy, SciPy, Statsmodels | Interval analysis and forecasts |
| ML | Scikit-learn | Lightweight classification/anomaly signals |
| LLM | Google Gemini API | Natural-language explanations and structured language tasks |
| AI integration | Direct API/SDK + function calling + Pydantic validation | Controlled orchestration |
| Storage | Azure Blob Storage | Private uploaded synthetic files |
| Identity | Microsoft Entra External ID or secure demo auth | Identity if setup fits schedule |
| Secrets | Azure Key Vault | Secret storage |
| Containers | Docker | Reproducible runtime |
| Hosting | Azure Container Apps | Managed container deployment |
| Registry | Azure Container Registry | Container image storage |
| Monitoring | Application Insights + Azure Monitor | Traces, logs and failures |
| Backend tests | Pytest | Unit/integration tests |
| E2E tests | Playwright + Testing Library | User journey and component tests |
| CI | GitHub Actions | Repeatable checks and deployment |

## Implementation notes
- Use current compatible stable versions at implementation time and pin them in lockfiles. Do not blindly assume versions from this document.
- Frontend uses Next.js App Router and strict TypeScript. Use one design-system approach; do not mix competing component libraries.
- FastAPI exposes REST endpoints under `/api/v1`. Every external request/response has a Pydantic schema.
- PostgreSQL is the canonical source of truth. Use NUMERIC for currency, constraints, indexes and migrations.
- pgvector is optional and only justified for retrieval of unstructured contextual notes. Structured financial facts remain relational.
- Polars is preferred for transformations; Pandas may be used where a library requires it.
- Gemini explains and assists with ambiguous language tasks. It does not calculate financial totals or make authoritative financial decisions.
- Use a deterministic fallback if Gemini is unavailable.

## Complexity to avoid
Do not introduce Kubernetes, Kafka, a fleet of microservices, multiple autonomous agents, a separate vector database, graph database or deep-learning models for every task unless measured needs justify them.

## Cost-aware fallbacks
If managed Azure PostgreSQL exceeds student credits, run PostgreSQL in Docker and preserve the same schema/migrations. If Redis hosting is too expensive, run Redis locally/containerized or process small demo jobs synchronously behind a job interface. If OCR is unreliable, make CSV and text-based PDF the P0 paths and clearly label scanned-PDF support as optional.

## Version policy
At project start, verify current stable package versions and compatibility from official documentation, pin dependencies, record versions in `DECISIONS_LOG.md` and avoid unneeded upgrades during the hackathon.

## Final decision
Use Next.js + TypeScript, FastAPI + Python, PostgreSQL + pgvector, Redis + Celery, deterministic analytics, Gemini for language assistance and Azure services where cost/availability make sense.
