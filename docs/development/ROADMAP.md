# Aikyra Development Roadmap

**Aikyra — "Many Minds. One Impact."**

Citizen reports a societal challenge → AI understands it → Problem DNA is generated → Challenge validated → Universities / experts / industry matched → Collaboration → Project created → Milestones and prototype → Deployment → Impact measurement.

> This roadmap is scoped for an **SIH hackathon prototype**, not an enterprise product. Keep the MVP small enough to finish before the deadline. Build vertical slices, demo early, demo often.

---

## Guiding Principles

1. **Vertical slice first** — one full journey (submit → store → retrieve → display) beats ten half-built features.
2. Do not implement every PS requirement immediately.
3. Prioritize demonstrable social impact.
4. Prefer explainable AI over black-box recommendations.
5. AI assists decisions; humans retain final authority.
6. No unnecessary microservices — one FastAPI app + PostgreSQL is enough.
7. Avoid paid infrastructure during development where possible.
8. Only introduce technologies that solve an actual problem.
9. Every phase has a clear Definition of Done (DoD).
10. Keep the MVP finishable before the SIH deadline.

---

## Phase 0 — Foundation

**Status: COMPLETE / IN PROGRESS**

- Git + GitHub
- React/Vite scaffold
- FastAPI scaffold
- PostgreSQL 17
- Project documentation
- Environment configuration
- SQLAlchemy
- Alembic

**DoD:** `docker-compose up` (or local services) boots frontend + backend + DB; Alembic migration runs cleanly; README explains setup.

---

## Phase 1 — Challenge Engine

**Priority: MVP**

Build:

- Citizen challenge submission
- Challenge storage
- Challenge retrieval
- Challenge detail page
- Basic challenge status
- Location
- Evidence upload architecture

Initial API:

```
POST   /api/challenges
GET    /api/challenges
GET    /api/challenges/{id}
PATCH  /api/challenges/{id}
```

**DoD:** A citizen can submit a challenge and retrieve it from PostgreSQL through the FastAPI API.

---

## Phase 2 — Problem DNA / AI

**Priority: MVP / CORE DIFFERENTIATOR**

Build:

- AI summarization
- Domain classification
- Subdomain classification
- Severity
- Urgency
- Affected population
- Required expertise
- Potential technologies
- SDG mapping
- Confidence score

Use:

- Ollama with a local LLM
- Structured JSON output (validated by Pydantic)

**DoD:** A submitted challenge can be transformed into structured Problem DNA.

**IMPORTANT:** AI recommendations must remain explainable and human-reviewable. Store raw model output alongside parsed DNA so judges can inspect both.

---

## Phase 3 — Challenge Discovery

**Priority: MVP**

Build:

- Challenge marketplace
- Search
- Filters: domain, district/location, severity
- Challenge detail page
- Problem DNA visualization

**DoD:** A user can find relevant challenges by search + filters and view full Problem DNA on the detail page.

---

## Phase 4 — Institutions & Matching (re-scoped into sub-phases)

### Phase 4A — Institution Foundation ✅ COMPLETE

Build:

- `Institution` entity (not "University") with `institution_type`: university / college / research_institute / innovation_hub
- Registration API: `POST /api/institutions` → always starts `active` + `unverified`
- Capability model: taxonomy-referenced `domains` + fixed-section validated JSONB `capabilities` (departments, expertise, research areas, technologies, facilities, incubation, prototyping, project experience, collaboration modes) — all human-entered
- Listing/search/filters/pagination: `GET /api/institutions`
- Profile retrieval + partial update: `GET/PATCH /api/institutions/{id}`
- Duplicate protection: service-level normalized check (409) + normalized DB unique index
- Trust fields: `verification_status`, `verification_note`, `verified_at`, `verified_by` (transitions wait for the auth phase)
- Frontend: `/institutions`, `/institutions/:id`, `/institutions/register` (+ edit mode)

**DoD:** An institution can register, appear in a filterable listing, be viewed and edited; duplicate names/websites are rejected with 409; all trust/lifecycle fields are established for future verification. No matching logic.

### Phase 4B — Deterministic Intelligent Matching ✅ COMPLETE

Implemented exactly as specified below: given Problem DNA, ranks **active + verified** institutions with an explainable, rule-based factor breakdown:

```
64 Match
+30  Domain relevance      (institutions.domains × DNA primary/secondary)
+19  Expertise overlap     (capabilities.expertise/disciplines × required_expertise)
+8   Research capability   (research_areas/technologies × solution_areas)
+4   Facilities            (facilities × solution/expertise tokens)
+5   Track record          (project_experience × keywords)
+8   Location relevance    (shared meaningful location tokens)
—    Urgency context       (critical/high bonus, gated on domain relevance)
```

- Endpoint: `GET /api/challenges/{id}/matches` (409 when DNA unreliable; empty pool returns 200).
- Eligibility gate enforced in SQL; recommendations computed per request, never persisted.
- Frontend: ranked "Recommended institutions" panel on the challenge detail page with score tiers and expandable factor breakdowns.
- Deterministic baseline labeled honestly (`rule-match-baseline-v1`) — embeddings/pgvector remain future work.

---

## Phase 4C — Authentication, Authorization & Verification ✅ COMPLETE

Build:

### Phase 4C Checkpoint 1 — Authentication Foundation
- User registration: `POST /api/auth/register` (email, password, full_name)
- User login: `POST /api/auth/login` (email, password) → JWT access token
- Current user: `GET /api/auth/me` (Bearer token) → user profile
- bcrypt password hashing (cost 12)
- Email normalization (lowercase, unique index on `lower(email)`)
- Duplicate registration protection (409)
- JWT: HS256, configurable expiration, stateless

### Phase 4C Checkpoint 2 — Institution Ownership & Authorization
- `institution_memberships` table linking users ↔ institutions
- Roles: `owner`, `representative`, `faculty`, `student`
- Statuses: `active`, `invited`, `suspended`
- Automatic owner membership on institution creation
- Owner/representative can PATCH institution
- Database-backed authorization (never trusts JWT claims)
- Mass-assignment protection: `extra='forbid'` on schemas

### Phase 4C Checkpoint 3 — Verification Workflow
- `pending_review` added to `institution_verification_status` enum
- State machine: `unverified` → `pending_review` → `verified` / `rejected` / `suspended`
- Owner/representative: `submit_for_review`, `resubmit` (after rejection)
- Platform reviewer (global Aikyra staff): `verify`, `reject`, `suspend`, `reinstate` on ANY institution
- Invalid transitions return 409
- Server-controlled audit fields: `verified_by`, `verified_at`, `verification_note`, `reviewer_user_id`
- Owner cannot self-verify (403)
- Verification badge UI: `unverified`, `pending_review`, `verified`, `rejected`, `suspended`

### Phase 4C — Platform Reviewer Architecture Correction
- Reviewer is a **platform-level** role (`users.is_platform_reviewer`), NOT an institution membership role
- Removed `reviewer` from `institution_membership_role`; added `faculty` and `student`
- A platform reviewer can verify any institution without being a member of it
- Institution owners/representatives cannot verify/suspend/reinstate
- Acknowledgement: Phase 5 CP1 (teams) already committed and left intact

### Phase 4C Checkpoint 4 — Development Seed Integration
- `seed_phase4c.py` — demo users + ADTU memberships
- `seed_local_demo.py` — integrates Phase 4C users/memberships
- `seed_phase4b.py` — integrates Phase 4C users/memberships
- Idempotent, development-only, never auto-executed

### Phase 4C Checkpoint 5 — Frontend Authentication
- `AuthContext`: session restoration, login, register, logout
- `/login`, `/register` pages with validation
- `ProtectedRoute` wrapper for `/institutions/register`
- `UserMenu` in navbar (Login/Register when logged out; Name/Logout when logged in)
- Automatic JWT attachment via API service
- 401 clears token + redirects; 403 shows permission error (no logout)
- Ownership-aware edit UI (checks `GET /api/institutions/{id}/membership`)

**DoD:** Users can register, login, logout, and session restores on refresh. Institution creation requires auth; editing requires active owner/representative membership. Verification workflow operates through backend state machine with server-controlled audit fields. Frontend displays correct verification statuses including `pending_review`. All 297 backend tests pass; frontend build passes.

---

## Phase 4D — Faculty / Student Team Workflow

Build:

- Faculty mentor assignment
- Student team formation
- Proposal
- Project creation

---

## Phase 6 — Industry Collaboration

**Priority: MVP / DEMO**

Build:

- Industry profiles
- Mentorship offers
- Funding offers
- Technical support
- Prototype support
- Pilot/deployment support

**DoD:** An industry profile can browse challenges/projects and attach an offer (mentorship / funding / pilot) visible to the university workspace.

---

## Phase 7 — Project Lifecycle

**Priority: MVP / DEMO**

Workflow:

```
Challenge → Validated → Matched → Accepted → Team formed
→ Proposal → Prototype → Pilot → Deployment → Impact
```

Build:

- Milestones
- Deliverables
- Status
- Progress
- Documentation

**DoD:** A project can be moved through every lifecycle stage, with milestones updating progress visibly.

---

## Phase 8 — Impact Measurement

**Priority: CORE DIFFERENTIATOR**

Track measurable outcomes such as:

- People affected
- Cost reduced
- Time saved
- Water saved
- Farmers benefited
- Villages reached
- CO2 reduced
- Other domain-specific metrics

Create an **Impact Score** / **Impact Dashboard**.

**IMPORTANT:** Aikyra measures whether solutions actually helped communities — not merely whether projects were completed.

**DoD:** A deployed project records domain-specific impact metrics and the dashboard computes and displays an Impact Score.

---

## Phase 9 — Government Dashboard

**Priority: DEMO**

Show:

- Total challenges
- Active projects
- University participation
- Industry participation
- Domain distribution
- District distribution
- Project completion
- Deployment
- Community impact

**DoD:** A single dashboard renders live aggregate stats (charts via Recharts, maps via Leaflet) from seeded demo data.

---

## Phase 10 — Communication

**Priority: POST-MVP**

- Notifications
- Status updates
- Collaboration requests
- Milestone notifications
- Basic messaging

Do **not** build a complex real-time chat system initially.

**DoD:** Users receive in-app notifications for status changes and collaboration requests.

---

## Phase 11 — Security & Trust

**Priority: BEFORE FINAL DEMO**

- Authentication
- Role-based authorization
- Input validation
- File validation
- Secure storage
- Audit logs
- Rate limiting
- Privacy controls
- AI confidence indicators
- Human approval for important decisions

**DoD:** All roles must log in; unauthorized API access is rejected; file uploads are validated; key decisions require human approval.

---

## Phase 12 — Deployment & SIH Demo

**Priority: FINAL**

- Production build
- Free/low-cost deployment
- Database deployment
- Environment configuration
- Seed demo data
- Demo accounts
- Error handling
- Loading states
- Responsive UI
- Final presentation workflow

**DoD:** Judges can open the deployed URL and complete the North Star Demo using provided demo accounts without errors or blank screens.

---

## Technology Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind CSS, React Router, Recharts, Leaflet |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL (pgvector later) |
| AI | Ollama + local LLM (Sentence Transformers later) |

---

## MVP vs Post-MVP

| Feature | MVP | Post-MVP |
|---|---|---|
| Challenge submission & storage | ✅ | |
| Problem DNA via local LLM | ✅ | |
| Discovery marketplace + filters | ✅ | |
| Explainable matching | ✅ | Semantic embeddings (pgvector), Sentence Transformers |
| University workspace | ✅ | |
| Industry offers | ✅ (simple forms) | Full negotiation workflows |
| Project lifecycle + milestones | ✅ | Gantt views, dependency tracking |
| Impact score + dashboard | ✅ | Automated impact verification |
| Government dashboard | ✅ (seeded data) | Live analytics, exports |
| Auth + basic RBAC | ✅ (before final demo) | SSO, granular permissions |
| Notifications | ❌ | In-app notifications, email |
| Messaging | ❌ | Simple messaging first, chat later |
| Evidence uploads | ✅ (architecture only) | Virus scanning, CDN |
| Real-time features | ❌ | Later |

---

## Phase Dependencies

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3
                │           │
                │           └──────► Phase 4 ──► Phase 5
                │                        │            │
                │                        ▼            ▼
                │                   Phase 6 ──► Phase 7
                │                                     │
                ├─────────────────────────────────────┘
                ▼                                      ▼
            Phase 8 ──► Phase 9                    Phase 10 (post-MVP)
                                                       │
        Phase 11 ◄── (before final demo) ◄─────────────┤
                │                                      │
                ▼                                      ▼
            Phase 12 ◄──────────────────────────────────┘
```

Hard rules:

- Phase 2 requires Phase 1 (DNA needs stored challenges).
- Phase 4 requires Phases 1–3 (matching ranks discoverable challenges).
- Phase 5–7 depend on Phase 4 (workspace exists because of matches).
- Phase 8 depends on Phase 7 (impact needs deployed projects).
- Phase 9 depends on Phase 8 (govt dashboard shows impact).
- Phases 11 → 12 come last but are non-negotiable before the final demo.

---

## Recommended Implementation Order

1. **Week 1:** Phase 0 wrap-up + Phase 1 (challenge CRUD end-to-end).
2. **Week 2:** Phase 2 (Ollama → Problem DNA) + start Phase 3.
3. **Week 3:** Finish Phase 3, build Phase 4 (rule-based scoring first; add semantic similarity if time allows). Start Phase 5.
4. **Week 4:** Phases 5–6, then Phase 7 lifecycle.
5. **Week 5:** Phase 8 impact metrics + Phase 9 government dashboard.
6. **Final week:** Phase 11 security essentials, Phase 12 deploy + seed data + rehearse demo.

Cut line if behind schedule: drop Phase 6 depth and Phase 9 polish first; never cut Phases 1, 2, 4, or 8 (they are the differentiators).

---

## Major Technical Risks

| Risk | Mitigation |
|---|---|
| Local LLM produces unreliable/unparseable JSON | Pydantic validation + retry prompt + fallback to rule-based extraction; keep human review step |
| Ollama too slow on demo hardware | Pre-generate DNA for seeded challenges; use smallest viable model |
| Matching feels arbitrary to judges | Deterministic weighted scoring with visible breakdown; hardcode sensible weights first |
| Scope creep across 13 phases | Enforce the cut line; MVP table is the contract |
| pgvector/embeddings complexity mid-hackathon | Ship keyword + rule-based matching first; add embeddings only if stable |
| Deployment surprises at the last minute | Deploy by end of week 5, not the final day; seed script runs locally and in prod |
| Team merge conflicts / broken main | Small PRs, feature branches, agreed API contract in Phase 1 |

---

## What We Deliberately Will NOT Build

- Microservices architecture
- Real-time chat / WebSockets
- Mobile apps (responsive web only)
- Payment processing
- Kubernetes / complex infra
- Multi-language support (beyond demo needs)
- Automated impact verification (manual entry for now)
- Custom ML model training
- Email/SMS gateways
- Admin CMS — seed scripts instead
- Every problem-statement requirement simultaneously

---

## SIH Demo-Critical Features

These must work flawlessly during judging:

1. Citizen submits a challenge with location (Phase 1)
2. AI generates readable Problem DNA live or from pre-seeded cache (Phase 2)
3. Marketplace browsing with filters (Phase 3)
4. **Explainable match score with factor breakdown** (Phase 4)
5. University accepts challenge → project created (Phases 5, 7)
6. Industry offer attached (Phase 6)
7. Impact dashboard showing real numbers (Phase 8)
8. Government dashboard overview (Phase 9)
9. Login as each role with demo accounts (Phases 11, 12)
10. Deployed URL + responsive UI (Phase 12)

---

## North Star Demo

The complete judge-facing story, end to end:

> A citizen in a drought-prone village submits: *"Our borewells are failing; 400 farming families lose their crops every summer."*
>
> Aikyra's AI reads the report and generates **Problem DNA**: domain — Water & Agriculture; severity — High; urgency — Seasonal; affected population — ~2,000 people; required expertise — hydrology, IoT sensing, agronomy; SDG 6 and SDG 2; confidence 87%. A reviewer confirms it in one click.
>
> The matching engine surfaces three universities:
>
> ```
> 94% Match — Regional Institute of Technology
>   +32 Expertise (hydrology faculty, agri-tech lab)
>   +25 Research (soil-moisture sensor papers)
>   +20 Laboratory (IoT & water testing labs)
>   +10 Previous Projects (village water audits)
>   + 7 Geographic relevance (same district)
> ```
>
> The university accepts, forms a student team under a faculty mentor, and writes a proposal. A local industry partner offers sensors and pilot funding. Milestones track the prototype → pilot → deployment path.
>
> Six months later, the Impact Dashboard shows: **1.2M litres of water saved, 380 farmers benefited, 12 villages reached, ₹40L input cost reduced — Impact Score 82/100.**
>
> On the Government Dashboard, the district officer sees the challenge, the project, and its measured impact — many minds, one impact.

If our prototype can walk this story live in under 10 minutes with no dead ends, we win the room.
