# Database

PostgreSQL 17 is the single datastore for Aikyra.

## Planned Structure

| Directory | Purpose |
|-----------|---------|
| `migrations/` | Alembic migration scripts (Alembic integration comes later) |
| `seeds/` | Seed data scripts (roles, reference data) |
| `schemas/` | SQL schema definitions and design references |

## Status

The complete schema is **not** designed yet. Current design direction lives in [docs/database/DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md).

## Local Setup

1. Ensure PostgreSQL 17 is running locally.
2. Create the database:

```sql
CREATE DATABASE aikyra;
```

3. Configure `DATABASE_URL` in `.env` (copy from `.env.example`).
