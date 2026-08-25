# AI Pipeline

> Phase 2 implemented the deterministic baseline stage of this pipeline. The Ollama LLM stage is planned, not built.

## Pipeline: Challenge → Problem DNA

```
┌─────────────┐   ┌──────────────┐   ┌─────────────────────────┐   ┌──────────────────┐
│  Challenge  │──▶│  Normalizer  │──▶│ Classifier (pluggable)  │──▶│ ProblemDnaService │
│    text     │   │ lower/strip  │   │ NOW: rule-baseline-v1   │   │ validate+persist  │
└─────────────┘   └──────────────┘   │ NEXT: Ollama LLM        │   └────────┬─────────┘
                                     └─────────────────────────┘            ▼
                                                              problem_dna table
                                                              status: pending_validation
                                                                     or needs_review
```

## Stages (current implementation)

1. **Preprocessing** (`services/classification/normalizer.py`) — lowercase, strip punctuation, word-boundary phrase matching.
2. **Classification** (`services/classification/rule_classifier.py`) — keyword scoring against `core/taxonomy.py`: primary + secondary domains, subdomain, urgency terms, stakeholder detection, geographic context, capped confidence.
3. **Persistence** (`services/problem_dna_service.py`) — maps the result onto the `problem_dna` model, sets `generated_by = deterministic_baseline` and `analyzer_version`, commits (service owns transactions).
4. **Human validation** — deferred until authentication exists; validated DNA is protected from automated overwrite (HTTP 409).

## Honest labeling

The current classifier is **not AI** and does not pretend to be: outputs carry `deterministic_baseline` as source. This gives a measurable baseline for comparing future LLM performance against.

## Future LLM Stage (planned)

- A classifier implementing the same `classify(title, description, location)` contract, selected behind the service boundary.
- Prompted JSON output → Pydantic validation → bounded retries → `needs_review` flag on failure.
- Ollama downtime never blocks existing endpoints; analysis remains explicitly triggered via `POST .../analyze`.

## Guardrails

- AI/deterministic output is always advisory; nothing becomes final without validation.
- Invalid or weak results route to `needs_review` — never silently accepted.
- Raw classifier evidence (`signals`) is persisted for explainability.

## Future Pipelines

- **Embedding pipeline** — sentence-transformers embeddings for challenges and institution profiles, stored in pgvector.
- **Matching pipeline** — see [MATCHING_ENGINE.md](MATCHING_ENGINE.md).
