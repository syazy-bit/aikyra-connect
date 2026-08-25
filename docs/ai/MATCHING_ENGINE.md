# Matching Engine

> Planned design. The matching algorithm is **not** implemented yet.

## Goal

Given a validated challenge (with Problem DNA), recommend the most relevant universities — and later, industry partners — with an explainable score.

## Signals to Consider

| Signal | Source | Notes |
|--------|--------|-------|
| Semantic similarity | Challenge embedding vs. university profile embedding | pgvector cosine similarity |
| University expertise | Declared domains, departments, research centers | Structured data |
| Faculty expertise | Faculty research areas mapped to Problem DNA "required expertise" | Structured + embeddings |
| Research areas | Publications/projects tagged by domain | Structured |
| Laboratory capabilities | Lab equipment/capabilities registry | Structured |
| Previous projects | Past project ↔ domain overlap | Historical signals |
| Student skills | Student skill profiles vs. "required technologies" | Structured |
| Industry capabilities | Partner org capability tags | Later phase |
| Geographic relevance | Distance between challenge location and institution | Rule-based weight |
| Implementation capacity | Track record of completed deployments | Historical signal |

## Scoring Approach (planned)

Hybrid scoring:

```
final_score = w1·semantic_similarity
            + w2·expertise_overlap
            + w3·capability_fit
            + w4·geographic_relevance
            + w5·track_record
```

- Weights start as configurable constants; tuned later against feedback.
- Every recommendation returns a **rationale string** ("Strong match: water-treatment research group; 40 km from challenge location").
- Output is a *recommendation list*, never an automatic assignment.

## Human-in-the-Loop

The engine recommends; humans decide. Universities accept or decline matches. AI does not independently make final institutional or project decisions.

## Phased Delivery

1. **v0:** Semantic similarity only, hardcoded seed universities.
2. **v1:** Hybrid structured + semantic scoring with weights.
3. **v2:** Learning-to-rank from acceptance feedback (scikit-learn).
