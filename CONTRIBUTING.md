# Contributing to Aikyra

Thanks for contributing! This document defines how our 5-member team works together.

## Team Structure & Ownership

| Member | Focus Area | Primary Directories |
|--------|-----------|---------------------|
| Member 1 | Frontend / Product Experience | `frontend/` |
| Member 2 | Backend / Database | `backend/`, `database/` |
| Member 3 | AI / ML | `ai/` |
| Member 4 | Matching / Analytics | `ai/matching/`, analytics modules |
| Member 5 | Product / Domain / Dataset / Integration | `docs/product/`, datasets, cross-cutting integration |

Ownership is a guideline, not a wall — everyone reviews and can contribute across areas, but the owner of an area has final say on its design.

## Getting Started

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in local values (never commit it).
3. Follow [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md).

## Branching

- `main` — stable, protected. No direct feature development.
- `develop` — integration branch for ongoing work.
- Feature branches: `feature/frontend-...`, `feature/backend-...`, `feature/ai-...`, `feature/matching-...`, `feature/docs-...`

Details: [docs/development/BRANCHING_STRATEGY.md](docs/development/BRANCHING_STRATEGY.md)

## Pull Requests

1. Branch off `develop`.
2. Keep PRs small and focused on one concern.
3. Ensure the app still runs and relevant tests pass.
4. Request review from the area owner plus at least one other member.

## Code Quality Rules

- Use clear, descriptive naming.
- Keep modules small; avoid unnecessary abstraction.
- Add comments only where they provide real value.
- Do not duplicate logic.
- Never hardcode secrets — use environment variables.
- Never commit `.env` or any credentials.
- Write code that is easy for students to understand and maintain.

## Documentation

Architectural decisions and plans belong under `docs/`. When you make a decision that affects other members, document it before or alongside the code change.
