# Aikyra

## Many Minds. One Impact.

Aikyra is a collaborative societal innovation platform that connects citizens and communities with universities, students, researchers, industry, startups, and government stakeholders — transforming real-world societal challenges into measurable solutions.

> **Status:** Phase 4C complete (Authentication, Authorization & Verification). Implemented so far: challenge engine (Phase 1), Problem DNA deterministic classifier (Phase 2), challenge discovery (Phase 3), institution/university foundation (Phase 4A), deterministic institution matching (Phase 4B), user authentication with JWT, institution ownership with database-backed memberships, verification workflow with state machine, frontend auth integration, protected routes, ownership-aware UI. Phase 4D (faculty/student team workflow) is next.

---

## Problem Statement

Societal problems in India (and beyond) are often reported but rarely converted into structured, solvable projects. There is no systematic bridge between:

- Citizens who experience problems on the ground,
- Universities and students who have the expertise and manpower to solve them,
- Industry and startups that can help scale solutions, and
- Government departments that need measurable impact data.

Aikyra aims to close this gap with a single collaborative platform.

## Vision

Every validated societal challenge becomes a well-understood problem ("Problem DNA"), is matched to the right collaborators, progresses through a guided project lifecycle, and ends with measured, verifiable impact.

## Core Workflow

```
Challenge
  → AI Understanding
  → Problem DNA
  → Validation
  → Intelligent Matching
  → University + Industry Collaboration
  → Project
  → Prototype
  → Deployment
  → Impact Measurement
```

## Main Stakeholders

1. Citizen / Community Member
2. University Student
3. Faculty / Mentor
4. University Administrator
5. Industry / Startup / MSME
6. Government / Department
7. Platform Administrator

See [docs/product/USER_ROLES.md](docs/product/USER_ROLES.md) for details.

## Planned Technology Stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | React + Vite (JavaScript), Tailwind CSS, React Router, Recharts, Leaflet (later) |
| Backend   | Python, FastAPI, Pydantic, SQLAlchemy |
| Database  | PostgreSQL 17 |
| AI        | Ollama (local LLM), sentence-transformers, scikit-learn, pgvector (later) |
| DevOps    | Git, GitHub, Docker (later) |

## Repository Structure

```
aikyra/
├── frontend/          React + Vite application
├── backend/           FastAPI REST API
├── ai/                AI services (Ollama, embeddings, matching)
├── database/          Migrations, seeds, SQL schemas
├── docs/              Product, architecture, API, database, AI, development docs
├── .env.example       Environment variable template (placeholders only)
└── README.md
```

## Development Roadmap

- **Phase 0 (complete):** Repository scaffolding, documentation, runnable skeleton.
- **Phase 1 (complete):** Challenge submission → storage → retrieval.
- **Phase 2 (complete):** Deterministic rule-based Problem DNA classifier (explicit baseline; AI-augmentation is a future seam).
- **Phase 3 (complete):** Challenge discovery — search, filters, sorting, pagination, related challenges.
- **Phase 4A (complete):** Institution foundation — registration (`POST /api/institutions`), capability profiles (domains from the taxonomy API + validated JSONB capability sections), listing/detail/edit UI, lifecycle + verification trust fields. Institutions register as *unverified*; only verified+active institutions participate in matching.
- **Phase 4B (complete):** Deterministic institution matching — `GET /api/challenges/{id}/matches` ranks verified+active institutions against Problem DNA with a transparent weighted breakdown and human-readable reasons; "Recommended institutions" panel on the challenge detail page; dev-only seed script (`backend/scripts/seed_phase4b.py`). Rule-based baseline (`rule-match-baseline-v1`) — no embeddings/AI.
- **Phase 4C (complete):** Authentication, authorization & verification — user registration/login/JWT (`/api/auth`), database-backed institution memberships (`owner`, `representative`, `reviewer`), automatic owner membership on creation, protected institution PATCH, verification state machine (`unverified` → `pending_review` → `verified`/`rejected`/`suspended`), server-controlled audit fields (`verified_by`, `verified_at`, `verification_note`), frontend auth (AuthContext, Login/Register, ProtectedRoute, UserMenu, JWT auto-attach, 401/403 handling), ownership-aware edit UI.
- **Phase 4D:** Faculty/student team workflow.
- **Later:** Industry collaboration, project lifecycle, impact measurement, government dashboard, notifications.

See [docs/development/BRANCHING_STRATEGY.md](docs/development/BRANCHING_STRATEGY.md) and [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md) to get started.
