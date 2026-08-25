# API Conventions

> Conventions for the Aikyra FastAPI REST API. Currently only `GET /health` exists; these rules govern all future endpoints.

## General

- Base URL: `/api/v1/...` for versioned resources (health endpoint stays at `/health`).
- JSON only. All responses use `Content-Type: application/json`.
- Resources are plural nouns: `/challenges`, `/universities`, `/projects`.
- No verbs in URLs — actions are expressed via HTTP methods.

## HTTP Methods

| Method | Usage | Success |
|--------|-------|---------|
| GET | Read resource(s) | 200 |
| POST | Create resource | 201 |
| PATCH | Partial update | 200 |
| PUT | Full replace (rare) | 200 |
| DELETE | Remove | 204 |

## Response Shape

Success:
```json
{ "data": { ... } }
```

Error (FastAPI/Pydantic style):
```json
{
  "detail": "Human-readable message"
}
```

List responses will include pagination metadata once needed.

## Validation

- All request/response bodies are Pydantic schemas (`backend/app/schemas`).
- Separate schemas for create vs. read (e.g., `ChallengeCreate`, `ChallengeRead`) so internal fields never leak.

## Naming

- JSON fields: `snake_case`.
- Query params: `snake_case`, e.g. `?domain=water&limit=20&offset=0`.

## AI Outputs

Any AI-generated content returned by the API must include its confidence score and validation status, and be clearly identified as advisory/recommendation data.

## Errors & Status Codes

Use standard codes: 400 (bad input), 404 (not found), 409 (conflict), 422 (validation), 500 (server). Never invent custom status semantics.

## Versioning

Breaking changes require a new version prefix (`/api/v2`). Additive changes stay within the current version.
