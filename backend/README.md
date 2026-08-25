# Backend — Aikyra REST API

FastAPI application. Currently contains only the scaffolding and a health endpoint.

## Structure

```
backend/
├── app/
│   ├── api/            Route handlers (routers)
│   ├── core/           Configuration, settings, security primitives
│   ├── models/         SQLAlchemy ORM models
│   ├── schemas/        Pydantic request/response schemas
│   ├── services/       Business logic
│   ├── repositories/   Database access layer
│   ├── utils/          Shared helpers
│   └── main.py         Application entry point
└── tests/              Test suite
```

## Run (development)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (bash: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

## Status

No business APIs are implemented yet. The MVP flow is documented in [docs/product/MVP_SCOPE.md](../docs/product/MVP_SCOPE.md).
