# Database Design

> Documents **what is currently implemented** (Phase 1 Challenge Engine, Phase 2 Problem DNA, Phase 3 Discovery search, Phase 4A Institution Foundation, **Phase 4C Authentication, Authorization & Verification**). Future entities are listed at the bottom as direction only.

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

**Indexes:** PK on `id`, `ix_challenges_status` on `status`, `ix_challenges_created_at` on `created_at` (listing order), and — added in Phase 3 — a generated `search_vector tsvector` column (`to_tsvector('english', title + description + location)`, always DB-maintained) with GIN index `ix_challenges_search_vector` powering full-text discovery search.

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

**Indexes:** PK on `id`, unique constraint on `challenge_id`, plus `ix_problem_dna_primary_domain` (btree, Phase 3) backing domain-filtered discovery queries.

**Data-ownership distinction:** citizen input lives only in `challenges`; `generated_by` distinguishes deterministic/AI/human provenance; `validation_status` separates advisory data from human-confirmed truth.

### `institutions`

A higher-education institution, research institute or innovation hub participating in the ecosystem (revision `b7d4e9a1c3f6`, Phase 4A). Capability data is **100% human-entered** — it is the input surface for the future deterministic matching engine; no matching semantics live in this table.

| Column | Type | Constraints / Notes |
|---------------------------|-------------------------------|------------------------------------------------------|
| `id` | `UUID` | Primary key |
| `name` | `VARCHAR(250)` | NOT NULL |
| `institution_type` | `institution_type` (enum) | university / college / research_institute / innovation_hub |
| `description` | `TEXT` | Nullable |
| `location` | `VARCHAR(200)` | NOT NULL (free text, same convention as challenges) |
| `website` | `VARCHAR(500)` | Nullable, http(s) URL validated at API layer |
| `contact_email` | `VARCHAR(254)` | Nullable |
| `domains` | `JSONB` | NOT NULL, default `'[]'`. Taxonomy domain slugs; validated against `app/core/taxonomy.py` on every write |
| `capabilities` | `JSONB` | NOT NULL, default `'{}'`. Fixed additive sections: departments, disciplines, expertise, research_areas, technologies, facilities, innovation_support, prototyping, project_experience, collaboration_modes. Unknown sections rejected; empty sections not persisted |
| `status` | `institution_status` (enum) | active / inactive; lifecycle visibility, default `active` |
| `verification_status` | `institution_verification_status` (enum) | unverified / verified / rejected / suspended; trust status, default `unverified`. Transitions belong to reviewers with roles (auth phase). Only `active` + `verified` institutions participate in future matching |
| `verification_note` | `TEXT` | Nullable — reviewer remarks / rejection reason |
| `verified_at` | `TIMESTAMPTZ` | Nullable |
| `verified_by` | `UUID` | Nullable, deliberately NOT a foreign key (`users` does not exist yet); never populated pre-auth |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | NOT NULL, server defaults |
| `search_vector` | `TSVECTOR` | Nullable, DB-generated persisted (`to_tsvector('english', name + description + location)`), same technique as challenges |

**Indexes:** PK on `id`; unique functional index `uq_institutions_name_normalized` on `lower(btrim(regexp_replace(regexp_replace(name, '[^a-zA-Z0-9]+', ' ', 'g'), '\s+', ' ', 'g')))` — duplicate-name protection whose expression is mirrored exactly by `InstitutionService.normalize_institution_name`; btree indexes on type/status/verification_status; GIN (`jsonb_path_ops`) on `domains` powering future domain-overlap candidate queries; GIN on `search_vector` for full-text listing search.

**Duplicate protection layers:** service-level normalized conflict check (case, punctuation and whitespace insensitive → 409) + the DB unique index as the race-safe guard.

No foreign keys exist yet — institutions are independent roots, like challenges were in Phase 1. Challenge↔institution relationships (interest, acceptance, projects) are deliberately deferred to their own phases so capability data, recommendations and workflow state are never conflated.

**Matching note (Phase 4B):** there is intentionally **no matches table**. Recommendations (`GET /api/challenges/{id}/matches`) are computed per request from current `problem_dna` × `institutions` rows by a pure scoring function, so rankings can never go stale. The Phase 4A indexes (GIN on `domains`, btrees on status/verification) are sufficient at current scale; no matching-specific index was added.

### `users` (Phase 4C — revision `a1b2c3d4e5f6`)

User accounts for platform authentication.

| Column         | Type                       | Constraints / Notes                                   |
|----------------|----------------------------|-------------------------------------------------------|
| `id`           | `UUID`                     | Primary key                                           |
| `email`        | `VARCHAR(254)`             | NOT NULL                                              |
| `hashed_password` | `VARCHAR(255)`          | NOT NULL (bcrypt, cost 12)                            |
| `full_name`    | `VARCHAR(250)`             | Nullable                                              |
| `is_active`    | `BOOLEAN`                  | NOT NULL, default `true`                              |
| `is_verified`  | `BOOLEAN`                  | NOT NULL, default `false`                             |
| `created_at`   | `TIMESTAMPTZ`              | NOT NULL, server default `now()`                      |
| `updated_at`   | `TIMESTAMPTZ`              | NOT NULL, server default `now()`                      |

**Indexes:** PK on `id`; unique functional index `uq_users_email` on `lower(email)` for case-insensitive uniqueness and login lookups.

**Password handling:** passwords are **never stored in plaintext** — only bcrypt hashes. `hashed_password` is populated by `AuthService.register()` via `passlib` with bcrypt rounds=12. Login verifies via `pwd_context.verify()`.

### `institution_memberships` (Phase 4C — revision `e7a2b8f1c3d4`)

Join table linking users to institutions with role and status. This is the **single source of truth for authorization** — no role information is trusted from JWT claims or client input.

| Column              | Type                       | Constraints / Notes                                   |
|---------------------|----------------------------|-------------------------------------------------------|
| `id`                | `UUID`                     | Primary key                                           |
| `user_id`           | `UUID`                     | NOT NULL, FK → `users.id` ON DELETE CASCADE           |
| `institution_id`    | `UUID`                     | NOT NULL, FK → `institutions.id` ON DELETE CASCADE    |
| `role`              | `institution_membership_role` (enum) | NOT NULL: `owner`, `representative`, `reviewer`       |
| `status`            | `institution_membership_status` (enum) | NOT NULL, default `active`: `active`, `invited`, `suspended` |
| `created_at`        | `TIMESTAMPTZ`              | NOT NULL, server default `now()`                      |
| `updated_at`        | `TIMESTAMPTZ`              | NOT NULL, server default `now()`                      |

**Constraints:**
- Unique constraint `uq_membership_user_institution` on `(user_id, institution_id)` — one membership per user per institution
- `ix_membership_institution` index on `institution_id`
- `ix_membership_user` index on `user_id`
- FK `user_id` → `users.id` ON DELETE CASCADE
- FK `institution_id` → `institutions.id` ON DELETE CASCADE

**Authorization rules (enforced in `MembershipRepository.has_role`):**
- Only `active` memberships grant permissions
- `owner` / `representative` → can PATCH institution (write access)
- `reviewer` → verification actions only (no institution edits)
- No membership → no permissions (403)

### `institution_verification_status` enum update (Phase 4C — revision `f3b9c2d1a8e7`)

Added `pending_review` to the existing enum using safe type replacement:
`unverified` | `pending_review` | `verified` | `rejected` | `suspended`

**State machine:**
- `unverified` → `pending_review` (owner/rep submits)
- `pending_review` → `verified` / `rejected` (reviewer decides)
- `verified` → `suspended` (reviewer suspends)
- `suspended` → `verified` (reviewer reinstates)
- `rejected` → `pending_review` (owner/rep resubmits)
- Invalid transitions rejected (409)

**Server-controlled audit fields (never client-settable):**
- `verified_by` (UUID of reviewer)
- `verified_at` (TIMESTAMPTZ)
- `verification_note` (reviewer remarks / rejection reason)
- `reviewer_user_id` (internal tracking)

## Data Access Conventions

1. Models live in `backend/app/models`, accessed only via `backend/app/repositories`.
2. Schema changes go exclusively through Alembic — no manual SQL or pgAdmin DDL.
3. Repositories flush only; services own transaction boundaries.
4. Table names: plural snake_case (`challenges`, `problem_dna`).
5. Every table: `id` primary key, `created_at`, `updated_at`.

## Direction Only (NOT implemented yet)

`users`, `challenge_interests` (Phase 4C), `projects`, `matches`, `embeddings` remain planned concepts from the architecture docs. They will be designed column-by-column when their roadmap phase begins.
