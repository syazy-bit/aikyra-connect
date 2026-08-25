# Problem DNA

> Phase 2A–2D implemented: data model, taxonomy, deterministic baseline, and API are live. LLM analysis is not.

## What is Problem DNA?

Problem DNA is Aikyra's structured profile of a societal challenge. It turns a free-text complaint into machine-usable understanding that will power validation, prioritization, deduplication, and matching.

## Data Ownership (implemented)

Every DNA row records where its content came from:

| Source | Value | Current producer |
|--------|-------|------------------|
| Deterministic baseline | `generated_by = deterministic_baseline` | Rule/keyword classifier (`rule-baseline-v1`) |
| AI model (future) | `generated_by = ai_model` | Ollama pipeline, not yet built |
| Human edit (future) | `generated_by = human` | Requires authentication |

`validation_status` separates advisory from authoritative:

```
pending_validation → validated          (human confirms; endpoint arrives with auth)
                 → needs_review         (confidence too low / no domain found)
```

**Rule:** automated output is never authoritative truth. Validated DNA is protected — re-running analysis on a validated DNA returns HTTP 409 instead of overwriting human work.

## Implemented Fields

| Field | Storage |
|-------|---------|
| `challenge_id` | UUID FK → `challenges.id`, unique (1:1), ON DELETE CASCADE |
| `primary_domain` / `secondary_domains` | taxonomy slug + JSONB list of runner-up slugs |
| `subdomain`, `problem_type`, `geographic_context` | nullable strings |
| `urgency` | native PG enum: low / medium / high / critical |
| `affected_stakeholders`, `keywords`, `required_expertise`, `potential_solution_areas` | JSONB arrays |
| `confidence_score` | numeric 0.00–1.00 |
| `signals` | JSONB map domain → matched keywords (**explainability**) |
| `analyzer_version` | e.g. `rule-baseline-v1` — reproducibility |
| `validation_status`, `validated_at` | human-validation gate |

The API response adds computed labels (`primary_domain_label`, `secondary_domain_labels`) resolved from the taxonomy so slugs in storage stay stable while labels can evolve.

## Taxonomy

14 controlled domains live in `backend/app/core/taxonomy.py` (Education, Healthcare, Agriculture, Water & Sanitation, Environment, Energy, Rural Livelihoods, Urban Development, Accessibility, Public Administration, Infrastructure, Transportation, Waste Management, Digital Services), each with subdomains, keywords, solution areas, and expertise. Access goes through helper functions only — a database-backed taxonomy can replace the constants later without touching classifier or service code.

## API (implemented)

| Method | Path | Behavior |
|--------|------|----------|
| POST | `/api/challenges/{id}/analyze` | Runs analysis, creates or regenerates DNA (409 if validated) |
| GET  | `/api/challenges/{id}/dna` | Returns stored DNA (404 if challenge or DNA missing) |

No PATCH endpoint yet: without authentication there is no way to authorize who may overwrite classifications, so human-edit is deferred to the auth phase.

## Rules

1. Every DNA row stores the analyzer version that produced it.
2. `confidence_score` and `signals` make every classification explainable.
3. Low confidence (< 0.45 — fewer than 3 distinct keyword hits) or no domain ⇒ `needs_review`, never silent acceptance.
4. Problem DNA is advisory input for future matching/validation — never an automatic decision.

See [AI_PIPELINE.md](AI_PIPELINE.md) for the generation flow.
