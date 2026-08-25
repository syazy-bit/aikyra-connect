# System Architecture

> Planned architecture. Current state: minimal skeletons only.

## High-Level Overview

```
┌──────────────────┐
│  React Frontend  │   Vite + Tailwind + React Router
│  (Vite dev:5173) │   Recharts (dashboards), Leaflet (maps, later)
└────────┬─────────┘
         │ REST (JSON) over HTTP
         ▼
┌──────────────────┐        ┌──────────────────┐
│  FastAPI Backend │──────▶│  Ollama (local)  │   AI inference,
│     (port 8000)  │        │  (port 11434)    │   later embeddings/ML
└────────┬─────────┘        └──────────────────┘
         │ SQLAlchemy ORM
         ▼
┌──────────────────┐
│   PostgreSQL 17  │   (pgvector extension planned for semantic search)
└──────────────────┘
```

## Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| Frontend | User experience, forms, visualization. No direct DB or AI access. |
| Backend API | Validation (Pydantic), business logic, orchestration of AI calls, persistence. |
| Database | Single source of truth. All entities and relationships. |
| AI services | Text understanding, Problem DNA generation, matching support. Stateless helpers called by the backend. |

## Key Decisions

1. **Single backend service** — no microservices at this stage. The `backend/app` package is organized by layer (`api`, `services`, `repositories`, `models`, `schemas`) so it can be split later if ever needed.
2. **AI behind the backend** — the frontend never talks to Ollama or ML models directly.
3. **Local-first AI** — Ollama keeps inference local; no external LLM APIs are required.
4. **Repository pattern** — database access goes through `app/repositories`, keeping business logic testable.
5. **Human-in-the-loop** — AI outputs are stored with confidence scores and marked advisory until validated.

## Request Flow (planned MVP example)

```
POST /challenges (frontend form)
  → FastAPI validates schema
  → Challenge row inserted via repository
  → Background task: call Ollama → generate Problem DNA → store
  → GET /challenges/{id} returns challenge + Problem DNA (with validation status)
```

## Request Flow (Phase 3 discovery)

```
GET /api/challenges?q=...&domains=a,b&urgencies=high&location=...&sort=relevance&skip&limit
  → FastAPI validates query params (taxonomy slugs, enums, bounds)
  → ChallengeService.discover()
  → DiscoveryRepository: LEFT JOIN challenges ⟕ problem_dna,
    full-text @@ websearch_to_tsquery on generated search_vector (GIN-indexed),
    filters, deterministic ordering, single COUNT subquery (no N+1)
  → Envelope response { items: [challenge + embedded dna summary], total, skip, limit }
```

Related-challenge recommendations (`GET /api/challenges/{id}/related`) are computed
deterministically from reliable Problem DNA only (confidence ≥ 0.45), with human-readable
reasons per suggestion. The taxonomy API (`GET /api/taxonomy`) is the single source of
truth for frontend filter options.

## Deployment (later)

Docker Compose with services: `frontend`, `backend`, `postgres`, `ollama`. Not set up yet.
