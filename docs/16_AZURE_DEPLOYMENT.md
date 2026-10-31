# 16 — Supabase Cloud Database & Deployment Guide

## Objective
PaisaFlow uses **Supabase** for its managed cloud PostgreSQL database. Supabase provides a 100% standard PostgreSQL 15/16 engine with pgvector support, an instant web-based Table Editor GUI, and a permanent Free Tier requiring zero credit card and zero cloud consumption billing.

---

## Service Mapping (100% Free Tier Stack)
| Need | Service | Notes |
|---|---|---|
| **Database** | **Supabase PostgreSQL** | Standard PostgreSQL with connection pooling & web GUI |
| **Authentication** | **Firebase Auth (Google OAuth)** | Popup OAuth with profile sync and UID mapping |
| **AI Intelligence** | **Google Gemini 3.5 Flash Lite** | Live conversational coaching with grounded context |
| **Backend Hosting** | **Render / Railway / Fly.io / Local** | FastAPI Python 3.11 with Uvicorn ASGI server |
| **Frontend Hosting** | **Vercel / Next.js Standalone** | Next.js 15 App Router |
| **Database Migrations** | **Alembic** | 4 versioned migrations applying cleanly to Supabase |

---

## Topology
- **Frontend**: Next.js App Router, Tailwind CSS 4, Motion/React, GSAP ScrollTrigger.
- **API**: FastAPI asynchronous ASGI application.
- **Database**: Supabase Managed PostgreSQL (`postgres` database on port 5432 / 6543).
- **AI Coach**: Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`).
- **Auth**: Firebase Google OAuth (`paisaflow06.firebaseapp.com`).

---

## Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?ssl=require

# Supabase Project Details
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# AI Coach
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Security & CORS
SESSION_SECRET=your_32_character_secret_key
CORS_ORIGINS=["http://localhost:3000","https://your-frontend.vercel.app"]
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Quick Setup Steps
1. Create a free project at [supabase.com](https://supabase.com).
2. Copy your PostgreSQL URI from **Settings → Database → Connection string → URI**.
3. Change `postgresql://` to `postgresql+asyncpg://` and append `?ssl=require`.
4. Update `DATABASE_URL` in `.env`.
5. Run migrations:
   ```bash
   python -m alembic -c backend/alembic.ini upgrade head
   ```
6. Open **Supabase Studio → Table Editor** to verify all tables.
