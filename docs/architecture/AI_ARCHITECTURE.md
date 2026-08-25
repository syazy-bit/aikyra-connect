# AI Architecture

> Planned architecture. No AI functionality is implemented yet.

## Principles

1. **AI assists, humans decide.** AI supports understanding and recommendations. It does not independently make final institutional or project decisions. Human validation is a mandatory workflow step.
2. **Local-first inference.** Ollama runs on local hardware; no external LLM APIs.
3. **Backend-mediated.** All AI calls are made by the FastAPI backend. The frontend never touches AI services directly.
4. **Explainability.** Every AI output (Problem DNA field, match score) carries a confidence value and human-readable rationale.

## Component Map

```
ai/
├── classifiers/    Challenge domain / severity classification   (planned)
├── embeddings/     sentence-transformers text embeddings        (planned)
├── matching/       Matching-engine support logic                (planned)
├── prompts/        Versioned prompt templates for Ollama        (planned)
├── pipelines/      End-to-end flows (e.g., Problem DNA gen)     (planned)
├── models/         Local model artifacts (not committed)        (planned)
└── tests/          Unit tests
```

## Model Strategy (planned)

| Task | Tool | Notes |
|------|------|-------|
| Structured analysis of challenge text | Ollama LLM | Prompted JSON output → Pydantic validation |
| Semantic similarity for matching | sentence-transformers | Stored as pgvector in PostgreSQL |
| Ranking / scoring refinements | scikit-learn | Hybrid scoring with rule-based signals |

## Data Flow: AI Understanding

```
Challenge text (backend)
  → pipeline selects prompt template (ai/prompts)
  → Ollama inference → raw JSON
  → Pydantic schema validation + confidence scoring
  → Problem DNA stored in PostgreSQL (status: "pending_validation")
  → Human validates/edits → status becomes "validated"
```

## Failure & Guardrails

- If Ollama is unavailable, challenges are still stored; Problem DNA generation retries later.
- All model outputs pass schema validation; invalid outputs trigger retry, then flag for manual review — never silent acceptance.

See also [AI_PIPELINE.md](../ai/AI_PIPELINE.md) and [PROBLEM_DNA.md](../ai/PROBLEM_DNA.md).
