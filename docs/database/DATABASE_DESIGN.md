# Database Design

> Documents **only what is currently implemented** (Phase 1). Future entities are listed at the bottom as direction only — they are not designed or created yet.

## Engine & Tooling

- PostgreSQL 17 (local dev)
- SQLAlchemy 2.x as ORM
- Alembic for migrations (`backend/migrations`)
- pgvector extension (planned, later) for embedding storage and similarity search

## Implemented Tables

### `challenges`

A societal challenge reported by a citizen. Created by Alembic revision `dbefd1316b42`.

| Column        | Type                       | Constraints                                    |
|---------------|----------------------------|------------------------------------------------|
| `id`          | `UUID`                     | Primary key, generated client-side (`uuid4`)   |
| `title`       | `VARCHAR(200)`             | NOT NULL                                       |
| `description` | `TEXT`                     | NOT NULL                                       |
| `location`    | `VARCHAR(200)`             | NOT NULL                                       |
| `status`      | `challenge_status` (enum)  | NOT NULL, default `'submitted'`, indexed       |
| `created_at`  | `TIMESTAMPTZ`              | NOT NULL, server default `now()`               |
| `updated_at`  | `TIMESTAMPTZ`              | NOT NULL, default `now()`, updated on change   |

**Enum type `challenge_status`:**

- `submitted`
- `under_review`
- `validated`
- `rejected`

Implemented as a native PostgreSQL enum so invalid statuses are impossible at the storage layer; the same values are mirrored by `ChallengeStatus` (Python `enum.Enum`) in `backend/app/models/challenge.py` and validated again by Pydantic on input.

**Indexes:** primary key on `id`, plus `ix_challenges_status` on `status` (status-driven filtering arrives with Phase 3 discovery).

**Design notes:**

- UUID primary keys avoid sequential-ID enumeration and work well across future service extraction.
- Timestamps are timezone-aware (`TIMESTAMPTZ`) with DB-side defaults; `updated_at` also updates via SQLAlchemy `onupdate`.
- Kept intentionally minimal — AI fields, evidence, reporter identity, etc. will be added through later migrations when those phases start.

## Data Access Conventions

1. Models live in `backend/app/models`, accessed only via `backend/app/repositories`.
2. Schema changes go exclusively through Alembic — no manual SQL or pgAdmin DDL.
3. Table names: plural snake_case (`challenges`).
4. Every table: `id` primary key, `created_at`, `updated_at`.

## Direction Only (NOT implemented yet)

`users`, `institutions`, `problem_dna`, `projects`, `matches`, `embeddings` remain planned concepts from the architecture docs. They will be designed column-by-column when their roadmap phase begins.
