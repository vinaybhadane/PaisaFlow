# PaisaFlow

**Tagline:** Your Money. Your Flow. Your Future.  
**Product:** AI-powered Personal Finance Coach with a Living Money Model  
**Hackathon market:** India | **Default currency:** INR | **Data:** Synthetic only

## 1. Product overview
PaisaFlow turns transaction records into a persistent, explainable and continuously updated model of a person's financial situation. It helps users understand cash flow, recurring commitments, budgets, savings goals and possible future scenarios. It learns from explicit user corrections and explains insights through an AI coach.

PaisaFlow is a decision-support and financial-education prototype. It is not a bank, payment processor, investment adviser, credit provider or tax adviser.

## 2. Problem
Most basic budgeting applications categorize transactions and stop. They often do not learn from corrections, identify irregular recurring commitments, preserve a time-aware financial profile, connect goals to cash flow, simulate future changes or explain nudges.

## 3. Product outcomes
A user can:
1. Explore a clearly labelled synthetic demo profile.
2. Import synthetic PDF/CSV statements or sample transaction notifications.
3. Review extracted transactions and correct errors.
4. See categories, merchant identities, confidence and evidence.
5. Understand recurring commitments and amount changes.
6. Maintain goals with target amounts and dates.
7. Run deterministic what-if simulations.
8. Ask questions grounded in their stored financial profile.
9. Receive evidence-backed spending nudges.
10. Review a monthly financial report.

## 4. Core modules
- Statement ingestion and normalization.
- Merchant resolution and hybrid categorization.
- User correction and rule-learning loop.
- Recurring-payment intelligence.
- Living financial profile and history.
- Budget and cash-flow analysis.
- Goal planning and progress.
- What-if simulation engine.
- AI coach and contextual memory.
- Nudges and monthly reviews.
- Security, privacy and data controls.

## 5. Technology summary
Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Apache ECharts.  
Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.  
Data: PostgreSQL with pgvector, Redis, Celery.  
Processing: Polars, Pandas, PyMuPDF, pdfplumber, PaddleOCR, RapidFuzz.  
Intelligence: deterministic rules, SciPy, Statsmodels, Scikit-learn, Google Gemini API.  
Cloud: Microsoft Azure where student-credit coverage and pricing make sense.  
Testing: Pytest, Playwright and Testing Library.

See `docs/06_TECH_STACK.md` and `docs/16_AZURE_DEPLOYMENT.md` before selecting versions or provisioning services.

## 6. Documentation index
- `AGENTS.md`: agent instructions and non-negotiable rules.
- `docs/01_PRODUCT_VISION.md`: vision and principles.
- `docs/02_PROBLEM_STATEMENT.md`: challenge interpretation.
- `docs/03_FEATURE_SPECIFICATION.md`: functional requirements.
- `docs/04_USER_FLOWS.md`: end-to-end journeys.
- `docs/05_UI_UX_GUIDELINES.md`: landing page and app design.
- `docs/06_TECH_STACK.md`: stack and rationale.
- `docs/07_SYSTEM_ARCHITECTURE.md`: component and data flow.
- `docs/08_DATABASE_SCHEMA.md`: database model.
- `docs/09_AI_INTELLIGENCE_ENGINE.md`: AI, ML and memory.
- `docs/10_FINANCIAL_LOGIC.md`: formulas and simulation.
- `docs/11_SECURITY_PRIVACY.md`: security and privacy.
- `docs/12_SYNTHETIC_DATA_SPEC.md`: fictional data requirements.
- `docs/13_API_SPECIFICATION.md`: API contract.
- `docs/14_TESTING_ACCEPTANCE.md`: quality gates.
- `docs/15_IMPLEMENTATION_ROADMAP.md`: build sequence.
- `docs/16_AZURE_DEPLOYMENT.md`: cloud deployment.
- `EXPERIMENT_LOG.md`, `DECISIONS_LOG.md`, `PROGRESS.md`: operational tracking.

## 7. Suggested repository structure
```text
paisaflow/
├── AGENTS.md
├── README.md
├── EXPERIMENT_LOG.md
├── DECISIONS_LOG.md
├── PROGRESS.md
├── docs/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── public/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── intelligence/
│   │   ├── workers/
│   │   └── prompts/
│   ├── migrations/
│   └── tests/
├── synthetic-data/
│   ├── generators/
│   ├── fixtures/
│   └── generated/
├── infra/
│   ├── docker/
│   └── azure/
└── .env.example
```

## 8. Development principles
Build working vertical slices. Use synthetic data only. Financial calculations must be deterministic. AI responses must be grounded in stored facts and calculation outputs. Every inference must be explainable and correctable. No real bank integration, payment execution, subscription cancellation or investment recommendations.

## 9. Demo narrative
1. Explain the problem on the landing page.
2. Enter a synthetic demo profile.
3. Import a synthetic statement.
4. Review extraction and categorization.
5. Correct one category and demonstrate future rule learning.
6. Show recurring commitments and a possible price-change alert.
7. Show a profile update after rent/income changes.
8. Create a savings goal.
9. Run a what-if scenario and show exact arithmetic.
10. Ask the coach for a grounded explanation.
11. Show the monthly review and privacy boundary.

This repository begins as a specification package. Antigravity must inspect the existing repository and implement in the documented phases. No feature is complete until acceptance criteria pass.
