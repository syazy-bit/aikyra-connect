# AI Pipeline

> Planned pipeline. Not implemented yet.

## Pipeline: Challenge → Problem DNA

```
┌─────────────┐   ┌───────────────┐   ┌──────────────────┐   ┌────────────┐
│  Challenge  │──▶│ Preprocessing │──▶│  Ollama LLM      │──▶│ Validation │
│    text     │   │ (clean, trim) │   │  structured call │   │ (Pydantic) │
└─────────────┘   └───────────────┘   └──────────────────┘   └─────┬──────┘
                                                                   │
                                                     valid? ───────┤
                                                     no → retry → flag manual
                                                     yes ▼
                                                       ┌──────────────────────┐
                                                       │ Store Problem DNA    │
                                                       │ status: pending_     │
                                                       │ validation           │
                                                       └──────────┬───────────┘
                                                                  ▼
                                                       ┌──────────────────────┐
                                                       │ Human validation UI  │
                                                       │ citizen/faculty edit │
                                                       └──────────┬───────────┘
                                                                  ▼
                                                          status: validated
```

## Stages

1. **Preprocessing** — normalize challenge text, detect language, strip noise.
2. **LLM analysis** — send prompt template (`ai/prompts/`) to Ollama; request strict JSON.
3. **Schema validation** — parse into the Problem DNA Pydantic schema; compute confidence score.
4. **Persistence** — store with `pending_validation` status and model/prompt version metadata.
5. **Human validation** — a human reviews, edits, and confirms. Only then is it `validated`.

## Guardrails

- AI output is always advisory; nothing enters the workflow as final without validation.
- Invalid/malformed model output triggers bounded retries, then routes to manual review.
- Ollama downtime never blocks challenge submission — analysis runs asynchronously.

## Future Pipelines

- **Embedding pipeline** — generate embeddings for challenges and institution profiles (sentence-transformers), store in pgvector.
- **Matching pipeline** — see [MATCHING_ENGINE.md](MATCHING_ENGINE.md).
