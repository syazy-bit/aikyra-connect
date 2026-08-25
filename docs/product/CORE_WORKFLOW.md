# Core Workflow

> Planned product workflow. Describes the intended lifecycle of a challenge on Aikyra. Not implemented yet.

## Lifecycle

```
1. Challenge                  A citizen/community member submits a societal challenge.
2. AI Understanding           The backend sends the challenge text to local AI (Ollama)
                              for structured analysis.
3. Problem DNA                AI generates a structured "Problem DNA" profile
                              (domain, severity, affected population, SDGs, etc.).
4. Validation                 Humans review and validate the AI's understanding
                              (citizen confirms; moderators/faculty refine).
5. Intelligent Matching       The matching engine recommends relevant universities,
                              faculty expertise, and industry partners.
6. University + Industry      Matched stakeholders express interest and form a
   Collaboration              collaboration.
7. Project                    An approved collaboration becomes a tracked project
                              with goals, milestones, and team.
8. Prototype                  The team builds and iterates on a prototype.
9. Deployment                 The validated solution is deployed in the community.
10. Impact Measurement        Outcomes are measured and reported to all stakeholders,
                              including government departments.
```

## Key Principles

- **Human validation gates:** AI output (Problem DNA, matching recommendations) is advisory. Humans confirm or correct it before it advances the workflow.
- **Transparency:** All stakeholders see challenge status, decisions, and impact data.
- **Measurability:** Every deployed solution should map to measurable indicators (e.g., SDG-linked metrics).

## MVP Slice

The first milestone implements only: submission → storage → AI analysis → Problem DNA → display → university recommendations. See [MVP_SCOPE.md](MVP_SCOPE.md).
