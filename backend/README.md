# Backend — Aikyra REST API

FastAPI application (modular monolith). Currently implements the Phase 1 Challenge Engine vertical slice: citizen challenge submission → validation → PostgreSQL storage → retrieval.

## Structure

```
backend/
├── app/
│   ├── api/                     Route handlers (routers)
│   │   └── challenges.py        Challenge endpoints
│   ├── core/
│   │   ├── config.py            Environment/DATABASE_URL configuration
│   │   ├── database.py          SQLAlchemy engine, SessionLocal, Base, get_db
│   │   └── exceptions.py        App-level exceptions (NotFoundError)
│   ├── models/
│   │   └── challenge.py         Challenge ORM model + ChallengeStatus enum
│   ├── schemas/
│   │   └── challenge.py         Pydantic Create / Update / Response schemas
│   ├── services/
│   │   └── challenge_service.py Business logic
│   ├── repositories/
│   │   └── challenge_repository.py  Database access layer
│   ├── utils/                   Shared helpers
│   └── main.py                  Application entry point
├── migrations/                  Alembic migration environment
├── alembic.ini
├── requirements.txt
└── tests/                       pytest suite
```

## 1. Virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (bash: source .venv/bin/activate)
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure DATABASE_URL

Copy `.env.example` (repo root) to `backend/.env` or the repo-root `.env` and fill in real values:

```
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/aikyra
TEST_DATABASE_URL=postgresql://postgres:<password>@localhost:5432/aikyra_test
```

- Never hardcode passwords in source.
- Never commit `.env` (already gitignored).
- The database itself must exist (`CREATE DATABASE aikyra;`). Schema objects are created only via Alembic.

## 4. Alembic migrations

Run from `backend/`:

```bash
alembic upgrade head                                  # apply all migrations
alembic revision --autogenerate -m "describe change"  # create a new migration
alembic downgrade -1                                  # revert last migration
alembic current                                       # show applied revision
```

The connection URL is read from `DATABASE_URL` via `app.core.config`; it is never stored in `alembic.ini`.

## 5. Start FastAPI

```bash
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Interactive docs (Swagger): http://localhost:8000/docs

## 6. Run tests

```bash
python -m pytest -q
```

Tests run against a dedicated `aikyra_test` PostgreSQL database (auto-created from `TEST_DATABASE_URL`, or derived from `DATABASE_URL` by replacing the database name). Your development `aikyra` database is never touched by tests.

## API Endpoints

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/health`               | Health check                             |
| POST   | `/api/challenges`       | Create a challenge (201)                 |
| GET    | `/api/challenges`       | List challenges (`skip` ≥ 0, `limit` 1–100, default 20; ordered `created_at DESC`) |
| GET    | `/api/challenges/{id}`  | Get one challenge (404 if missing)       |
| PATCH  | `/api/challenges/{id}`  | Update `title` / `description` / `location` (404 if missing) |

Challenge fields: `id` (UUID), `title`, `description`, `location`, `status` (`submitted` | `under_review` | `validated` | `rejected`), `created_at`, `updated_at`.

Status is a workflow field — it is **not** modifiable through the public PATCH endpoint. Status transitions will be controlled by authorized reviewers once authentication and roles are introduced.

Transactions are owned by the service layer: repositories flush only, the service commits on success and rolls back on failure.

Errors: `422` for invalid request data, `404` for unknown IDs. Raw database errors are never returned to clients.

## Status

Phase 1 Challenge Engine backend slice complete. Next phases per [docs/development/ROADMAP.md](../docs/development/ROADMAP.md): AI Problem DNA (Phase 2), discovery (Phase 3).
