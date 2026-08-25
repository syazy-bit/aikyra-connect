# Branching Strategy

## Branch Model

```
main          stable, protected — releases only
  └── develop integration branch — all work lands here first
        ├── feature/frontend-...
        ├── feature/backend-...
        ├── feature/ai-...
        ├── feature/matching-...
        └── feature/docs-...
```

## Rules

1. **`main` is protected.** No direct commits, no direct feature development. Changes reach `main` only via reviewed merges from `develop` (release points).
2. **`develop` is the working integration branch.** Feature branches target `develop`.
3. **Feature branches are short-lived.** Branch → small PR → review → merge to `develop` → delete branch.

## Branch Naming

```
feature/<area>-<short-description>
```

| Area | Prefix | Examples |
|------|--------|----------|
| Frontend | `feature/frontend-` | `feature/frontend-challenge-form` |
| Backend | `feature/backend-` | `feature/backend-health-endpoint` |
| AI / ML | `feature/ai-` | `feature/ai-problem-dna-pipeline` |
| Matching | `feature/matching-` | `feature/matching-semantic-v0` |
| Docs | `feature/docs-` | `feature/docs-user-roles` |

## Workflow

```bash
git checkout develop
git pull
git checkout -b feature/backend-challenge-crud
# ...work, commit...
git push origin feature/backend-challenge-crud
# open PR into develop, request review from area owner + 1 other
```

## Commit Style

Short imperative messages, e.g. `add health endpoint to FastAPI app`.

## Versioning

`main` tags mark milestones (e.g., `v0.1.0-scaffold`). Semantic-ish versioning; exact scheme can evolve.
