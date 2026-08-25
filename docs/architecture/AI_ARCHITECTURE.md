# AI Architecture

> Phase 2 implemented the deterministic Problem DNA foundation. No LLM inference exists yet.

## Principles

1. **AI assists, humans decide.** AI supports understanding and recommendations. It does not independently make final institutional or project decisions. Human validation is a mandatory workflow step.
2. **Local-first inference.** Ollama runs on local hardware; no external LLM APIs.
3. **Backend-mediated.** All AI calls are made by the FastAPI backend. The frontend never touches AI services directly.
4. **Explainability.** Every output carries a confidence value and persisted evidence (`signals`).

## Component Map (current state)

```
backend/app/
├── core/taxonomy.py                    Controlled domain taxonomy (implemented)
├── services/classification/
│   ├── normalizer.py                   Text preprocessing (implemented)
│   ├── rule_classifier.py              Deterministic baseline classifier (implemented)
│   └── schemas.py                      ClassificationResult contract (implemented)
├── services/problem_dna_service.py     Orchestration + transactions (implemented)
├── repositories/problem_dna_repository.py  DB access (implemented)
├── models/problem_dna.py               problem_dna table (implemented)
└── api/problem_dna.py                  /analyze and /dna endpoints (implemented)

ai/                                     (future) prompts, pipelines, model artifacts
```

## Model Strategy

| Task | Tool | Status |
|------|------|--------|
| Structured analysis of challenge text | Rule/keyword classifier | **Implemented (baseline)** |
| Structured analysis of challenge text | Ollama LLM | Planned — same `classify()` contract, chosen behind the service boundary |
| Semantic similarity for matching | sentence-transformers → pgvector | Planned |

## Data Flow: AI Understanding (implemented flow, deterministic stage)

```
POST /api/challenges/{id}/analyze
  → ChallengeDnaService loads challenge
  → rule_classifier.classify(title, description, location)
  → ClassificationResult validated by Pydantic
  → problem_dna row stored (generated_by=deterministic_baseline,
    validation_status=pending_validation or needs_review)
  → GET /api/challenges/{id}/dna returns DNA with confidence + signals
```

## Failure & Guardrails

- Analysis never runs inside repositories or routes — only in services.
- Weak results (no domain, confidence < 0.45: fewer than 3 converging keyword hits) become `needs_review`.
- Validated DNA cannot be overwritten by automated re-analysis (409).
- No endpoint claims AI classification that did not happen; source is explicit.

See also [AI_PIPELINE.md](../ai/AI_PIPELINE.md) and [PROBLEM_DNA.md](../ai/PROBLEM_DNA.md).
