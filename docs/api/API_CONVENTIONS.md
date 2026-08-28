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

401/403 reserved for the auth phase. Phase 4C implements:
- **401 Unauthorized** — missing/invalid/expired JWT. Token cleared client-side, user redirected to login.
- **403 Forbidden** — authenticated but lacks membership/role for the action. User NOT logged out; permission error displayed.
- **422 Unprocessable Entity** — validation error (Pydantic, `extra='forbid'` prevents mass-assignment).
- **409 Conflict** — duplicate resource (institution name/website) or invalid verification state transition.
- Standard codes: 404, 500.

## Authentication Conventions (Phase 4C)

### JWT Bearer Token
- **Header:** `Authorization: Bearer <access_token>`
- **Algorithm:** HS256
- **Payload:** `sub` (user UUID), `iat`, `exp`
- **Expiration:** Configurable via `JWT_EXPIRE_MINUTES` (default 30 minutes)
- **Secret:** `JWT_SECRET_KEY` (environment variable)

### Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Public | Register new user |
| POST | `/api/auth/login` | Public | Login, returns JWT |
| GET | `/api/auth/me` | Required | Current user profile |
| POST | `/api/institutions` | Required | Create institution (auto-creates owner membership) |
| PATCH | `/api/institutions/{id}` | Required | Update (requires active owner/rep membership) |
| GET | `/api/institutions/{id}/membership` | Required | Caller's membership for institution |
| PATCH | `/api/institutions/{id}/verification` | Required | Verification workflow (owner/rep submit + platform reviewer actions) |

### Authorization Model
- **Database-backed:** `MembershipRepository.has_role(user_id, institution_id, roles)` queries `institution_memberships`; platform reviewer privilege is read from `users.is_platform_reviewer`
- **Never trusts:** JWT claims, client headers, URL parameters, body fields
- **Role matrix:**
  - `owner` / `representative` (active) → institution PATCH, submit_for_review, resubmit
  - Platform reviewer (`users.is_platform_reviewer = true`) → verify, reject, suspend, reinstate on ANY institution (no membership required)
  - `faculty` / `student` (active) → institution-scoped roles (Phase 5); no PATCH, no verification
  - No membership / inactive / invited / suspended → 403
- **Institution isolation:** Membership on institution A does not grant access to institution B. Platform reviewers are deliberately platform-wide for verification only; they gain no institution write access.

### Server-Controlled Fields (never client-settable)
| Field | Context | Set By |
|-------|---------|--------|
| `verified_by` | Institution verification | Platform reviewer (server, from auth) |
| `verified_at` | Institution verification | Server timestamp |
| `verification_note` | Institution verification | Platform reviewer (server) |
| `reviewer_user_id` | Verification request | Server (from auth) |
| `owner_user_id` | Institution creation | Server (from auth) |
| `role` | Membership | Server (endpoint logic) |
| `verification_status` | Institution | Server (state machine) |
| `is_platform_reviewer` | User | Server/admin only — never client-settable |

### Frontend Handling
- Token stored in `localStorage` as `aikyra_token`
- API service auto-injects `Authorization` header when token exists
- 401 → clears token, redirects to `/login`
- 403 → displays permission error, **does not logout**
- Session restored on app startup via `GET /api/auth/me`

## Versioning

Breaking changes require a new version prefix. Additive changes stay within the current path.
