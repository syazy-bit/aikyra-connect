# Aikyra

## Many Minds. One Impact.

Aikyra is a collaborative societal innovation platform that connects citizens and communities with universities, students, researchers, industry, startups, and government stakeholders — transforming real-world societal challenges into measurable solutions.

> **Status:** Initial scaffolding phase. The repository structure, documentation, and minimal runnable skeletons exist. No product features are implemented yet.

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

- **Phase 0 (current):** Repository scaffolding, documentation, minimal runnable skeleton.
- **Phase 1 (MVP):** Challenge submission → storage → AI analysis → Problem DNA generation → challenge display → university matching recommendations.
- **Phase 2:** Validation workflows, collaboration spaces, project lifecycle tracking.
- **Phase 3:** Prototyping support, deployment tracking, impact measurement dashboards.
- **Later:** Leaflet maps, pgvector semantic search, Docker deployment.


See [docs/development/BRANCHING_STRATEGY.md](docs/development/BRANCHING_STRATEGY.md) and [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md) to get started.
