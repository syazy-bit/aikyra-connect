# Database Design

> Planned design direction. The full schema is **not** created yet — no tables exist beyond what future migrations will define.

## Engine & Tooling

- PostgreSQL 17
- SQLAlchemy 2.x as ORM
- Alembic for migrations (integration planned)
- pgvector extension (planned) for embedding storage and similarity search

## Planned Core Entities

| Entity | Purpose |
|--------|---------|
| `users` | All users; role-based (7 roles, see USER_ROLES.md) |
| `institutions` | Universities, industry/orgs, government departments |
| `challenges` | Submitted societal challenges |
| `problem_dna` | Structured AI analysis of a challenge (1:1 with challenge) |
| `projects` | Collaboration projects formed from matched challenges |
| `matches` | Challenge ↔ university recommendations with scores |
| `embeddings` | Vector representations for semantic search |

## Design Principles

1. **Repository pattern in code** — models live in `backend/app/models`, accessed only via `backend/app/repositories`.
2. **Migrations over manual SQL** — schema changes go through Alembic once integrated.
3. **AI outputs are versioned data** — Problem DNA rows store the model/prompt version used, enabling reproducibility.
4. **Soft references to SDGs** — SDG mapping stored as structured data, not free text.

## Conventions (planned)

- Table names: plural snake_case (`challenges`, `problem_dna`).
- Every table: `id` primary key, `created_at`, `updated_at`.
- Foreign keys explicit and named (`challenge_id`).

Detailed column-level design will be added here when the MVP schema is drafted.
