# AI — Aikyra AI Services

This directory will host Aikyra's local AI components (Ollama-based LLM inference, embeddings, matching support). **Nothing is implemented yet** — this is a planned structure.

## Planned Structure

| Directory | Purpose |
|-----------|---------|
| `classifiers/` | Challenge domain/severity classification (later) |
| `embeddings/` | Text embedding generation via sentence-transformers (later) |
| `matching/` | Matching engine logic shared with Member 4's work (later) |
| `prompts/` | Versioned prompt templates for Ollama (later) |
| `pipelines/` | End-to-end pipelines, e.g. Problem DNA generation (later) |
| `models/` | Local model artifacts and metadata (never commit large binaries) |
| `tests/` | Unit tests for AI components |

## Guiding Principle

AI **assists** with understanding and recommendations. AI does **not** independently make final institutional or project decisions — human validation remains part of the workflow at all times.

## Design Notes

- AI services are called through the FastAPI backend, never directly from the frontend.
- Ollama runs locally (`http://localhost:11434` by default).
- See [docs/ai/AI_PIPELINE.md](../docs/ai/AI_PIPELINE.md), [docs/ai/PROBLEM_DNA.md](../docs/ai/PROBLEM_DNA.md), and [docs/architecture/AI_ARCHITECTURE.md](../docs/architecture/AI_ARCHITECTURE.md).
