# MVP Scope

> The first actual product milestone. **Not implemented yet** — this document defines what we will build.

## MVP Flow

```
Citizen submits a societal challenge
  → Backend stores it
  → AI analyzes it
  → Aikyra generates Problem DNA
  → Challenge is displayed
  → Matching engine recommends relevant universities
```

## In Scope

1. Challenge submission (frontend form + backend endpoint).
2. Challenge persistence in PostgreSQL.
3. AI analysis of challenge text via local Ollama inference.
4. Problem DNA generation and storage.
5. Challenge display page.
6. Basic matching recommendations: relevant universities for a challenge.

## Out of Scope (for MVP)

- Authentication and full role-based access.
- Validation workflow UI.
- Project / prototype / deployment lifecycle tracking.
- Impact measurement dashboards.
- Industry/government onboarding portals.
- Maps (Leaflet), advanced analytics.

## Success Criteria

- A user can submit a challenge end-to-end through the UI.
- Problem DNA is generated, stored, and visible on the challenge page.
- University recommendations are returned with human-readable rationale.
- AI outputs are clearly marked as *recommendations pending validation*.

## Suggested Build Order

| Step | Deliverable | Owner |
|------|------------|-------|
| 1 | DB schema for challenges + universities | Member 2 |
| 2 | Challenge CRUD API | Member 2 |
| 3 | Submission form + challenge page shell | Member 1 |
| 4 | Ollama analysis pipeline + Problem DNA schema | Member 3 |
| 5 | Matching engine v0 (semantic similarity) | Members 3 & 4 |
| 6 | Domain/data quality review, seed university data | Member 5 |
