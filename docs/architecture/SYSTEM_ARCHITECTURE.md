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

## Deployment (later)

Docker Compose with services: `frontend`, `backend`, `postgres`, `ollama`. Not set up yet.
