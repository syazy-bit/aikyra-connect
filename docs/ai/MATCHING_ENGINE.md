# Matching Engine

> Describes the **implemented Phase 4B deterministic baseline** (`rule-match-baseline-v1`). Future enhancements are marked explicitly as future work at the bottom.

## Goal

Given a challenge with reliable Problem DNA, recommend the most capable **verified + active** institutions — with a fully explainable score. The engine recommends; humans decide.

## Implemented Architecture (Phase 4B)

Deterministic rule-based scoring in the service layer:

```
Challenge / Problem DNA
        ↓
SQL candidate selection   (verified + active gate enforced in the query;
        ↓                  GIN-indexed JSONB domain containment narrows first)
Python scoring            (pure function `match_institution`, no persistence)
        ↓
Ranked recommendations    (score desc, then name asc; MIN_MATCH_SCORE = 15)
        ↓
Score + factor breakdown + human-readable reasons
```

- Candidate pool is capped (1000) and widened when domain filtering yields too few candidates.
- Recommendations are **computed on every request and never persisted** — rankings can never go stale.
- No client parameter can influence weights, thresholds, pool size, or eligibility.

## Scoring Factors (total = 100)

| Factor | Max | Inputs |
|---|---|---|
| Domain relevance | 35 | DNA primary (25) + secondary domains (5 each, ≤2) × institution.domains |
| Expertise overlap | 25 | DNA required_expertise × capabilities.expertise ∪ disciplines (ratio-proportional) |
| Research capability | 15 | DNA potential_solution_areas × capabilities.research_areas ∪ technologies |
| Facilities | 5 | matched facility items × solution/expertise tokens |
| Project experience | 5 | experience items sharing keyword/expertise tokens |
| Location relevance | 10 | shared meaningful location tokens (`extract_location_tokens`; stop-words never match) |
| Urgency modifier | 5 | critical = 5 / high = 3, only when domain points > 0 |

Text overlap uses normalized word tokens (lowercase, ≥3 chars, generic words dropped, simple plural folding), rounded half-up for ratio factors. Every response item satisfies the invariant `sum(breakdown[factor].points) == score`, and every non-zero factor exposes its matched evidence.

**DNA eligibility gate:** `primary_domain` present AND `confidence_score >= 0.45` — otherwise the API returns 409 ("run analysis first"), mirroring related-challenge reliability rules.

## Human-in-the-Loop

Output is a *recommendation list*, never an assignment. Institutions decide whether to engage (challenge-interest workflow arrives in Phase 4C).

## Explicitly NOT Implemented (future work)

The following earlier drafts are **not** part of the shipped system:

- Semantic similarity / embeddings / pgvector
- Faculty or student skill profiles (no such tables exist)
- Geocoding, coordinates, "km distance" — location matching is token-based
- Learning-to-rank from acceptance feedback

These plug in behind `match_institution()` without changing routes,
repositories, or the response contract.
