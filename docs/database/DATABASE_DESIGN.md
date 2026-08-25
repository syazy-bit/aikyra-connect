# Database Design

> Documents **what is currently implemented** (Phase 1 Challenge Engine + Phase 2 Problem DNA foundation). Future entities are listed at the bottom as direction only.

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

**Enum type `challenge_status`:** `submitted`, `under_review`, `validated`, `rejected`.

**Indexes:** PK on `id`, `ix_challenges_status` on `status`, `ix_challenges_created_at` on `created_at` (listing order).

### `problem_dna`

Structured system-derived understanding of a challenge (revision `4140091755aa`). 1:1 with challenges via unique FK with `ON DELETE CASCADE`. Everything here is **system-derived or human-refined — never citizen input**; automated rows stay advisory (`pending_validation`) until human validation.

| Column                    | Type                        | Constraints / Notes                                   |
|---------------------------|-----------------------------|-------------------------------------------------------|
| `id`                      | `UUID`                      | Primary key                                            |
| `challenge_id`            | `UUID`                      | NOT NULL, UNIQUE FK → `challenges.id`, CASCADE delete  |
| `primary_domain`          | `VARCHAR(50)`               | Taxonomy slug from `app/core/taxonomy.py`; nullable    |
| `secondary_domains`       | `JSONB`                     | Array of runner-up domain slugs                        |
| `subdomain`               | `VARCHAR(100)`              | Nullable                                               |
| `problem_type`            | `VARCHAR(100)`              | Nullable                                               |
| `geographic_context`      | `VARCHAR(50)`               | rural / semi_urban / urban; nullable                   |
| `urgency`                 | `urgency_level` (enum)      | low / medium / high / critical; default `medium`       |
| `affected_stakeholders`   | `JSONB`                     | e.g. ["Farmers", "Children"]                           |
| `keywords`                | `JSONB`                     | Matched evidence terms                                 |
| `required_expertise`      | `JSONB`                     | Disciplines needed                                     |
| `potential_solution_areas`| `JSONB`                     | Candidate solution directions                          |
| `confidence_score`        | `NUMERIC(3,2)`              | 0.00–1.00                                              |
| `signals`                 | `JSONB`                     | Map domain → matched keywords (explainability)         |
| `generated_by`            | `dna_source` (enum)         | deterministic_baseline / ai_model / human              |
| `analyzer_version`        | `VARCHAR(50)`               | e.g. `rule-baseline-v1`                                |
| `validation_status`       | `dna_validation_status`(enum)| pending_validation / validated / needs_review          |
| `validated_at`            | `TIMESTAMPTZ`               | Set when humans validate (auth phase)                  |
| `created_at` / `updated_at` | `TIMESTAMPTZ`             | NOT NULL, server defaults                              |

Multi-valued attributes use JSONB arrays rather than child tables for now — queryable and GIN-indexable later without premature joins. Normalization into child tables is an evolution path if filtering requirements demand it.

**Data-ownership distinction:** citizen input lives only in `challenges`; `generated_by` distinguishes deterministic/AI/human provenance; `validation_status` separates advisory data from human-confirmed truth.

## Data Access Conventions

1. Models live in `backend/app/models`, accessed only via `backend/app/repositories`.
2. Schema changes go exclusively through Alembic — no manual SQL or pgAdmin DDL.
3. Repositories flush only; services own transaction boundaries.
4. Table names: plural snake_case (`challenges`, `problem_dna`).
5. Every table: `id` primary key, `created_at`, `updated_at`.

## Direction Only (NOT implemented yet)

`users`, `institutions`, `projects`, `matches`, `embeddings` remain planned concepts from the architecture docs. They will be designed column-by-column when their roadmap phase begins.
