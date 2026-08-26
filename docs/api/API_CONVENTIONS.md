# API Conventions

> Conventions for the Aikyra FastAPI REST API. These describe the conventions **actually used by the implemented API** (Phases 1–4A). The originally drafted `/api/v1` prefix and `{data: ...}` envelope were not adopted; this document reflects reality.

## General

- Resource base path: `/api/<plural>` (e.g. `/api/challenges`, `/api/institutions`). Health stays at `/health`.
- JSON only. All responses use `Content-Type: application/json`.
- Resources are plural nouns: `/challenges`, `/institutions`. No verbs in URLs.
- UUID identifiers in paths.

## HTTP Methods

| Method | Usage | Success |
|--------|-------|---------|
| GET | Read resource(s) | 200 |
| POST | Create resource | 201 |
| PATCH | Partial update (workflow/trust fields excluded from payloads) | 200 |

## Response Shape

Single resources are returned as bare objects:

```json
{ "id": "...", "name": "..." }
```

List endpoints use the pagination envelope:

```json
{ "items": [...], "total": 42, "skip": 0, "limit": 20 }
```

Errors use FastAPI/Pydantic style:

```json
{ "detail": "Human-readable message" }
```

(`detail` may be an array of `{loc, msg, type}` objects on 422 validation errors.)

## Validation

- All request/response bodies are Pydantic schemas (`backend/app/schemas`).
- Separate schemas for create vs. read vs. update so internal fields never leak.
- Query parameters are validated via Pydantic query models bound with `Annotated[Model, Query()]`.
- Multi-value query params accept both repeated keys (`domains=a&domains=b`) and CSV (`domains=a,b`).
- Taxonomy-referenced values (domain slugs) are always validated against the controlled taxonomy (`app/core/taxonomy.py`) — never against hardcoded frontend lists.

## Layering Rules

Router → Service → Repository → Model.

- Routers contain no business logic.
- Services own transaction boundaries and duplicate/conflict checks.
- Repositories flush only, never commit, and contain no HTTP concerns.

## Naming

- JSON fields: `snake_case`.
- Query params: `snake_case`; pagination uses `skip`/`limit`.

## AI / Deterministic Outputs

Any system-derived content must include provenance (`generated_by`, `analyzer_version`) and a validation status, and be clearly identified as advisory/recommendation data. Rule-based processing is labeled *deterministic baseline* — never "AI". Institution capability data is human-entered and carries no AI provenance.

## Errors & Status Codes

401/403 reserved for the auth phase (no fake security before then). Otherwise standard codes: 404 (`NotFoundError` → `{"detail": "<Entity> with id '...' not found"}`), 409 (`ConflictError`, e.g. duplicate institution name/website), 422 (validation), 500 (server).

## Versioning

Breaking changes require a new version prefix. Additive changes stay within the current path.
