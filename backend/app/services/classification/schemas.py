from pydantic import BaseModel

from app.models.problem_dna import DnaSource, UrgencyLevel


class ClassificationResult(BaseModel):
    """Output of a deterministic/AI classifier — the raw material for DNA."""

    primary_domain: str | None
    secondary_domains: list[str] = []
    subdomain: str | None = None
    problem_type: str | None = None
    geographic_context: str | None = None
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    affected_stakeholders: list[str] = []
    keywords: list[str] = []
    required_expertise: list[str] = []
    potential_solution_areas: list[str] = []
    confidence_score: float = 0.0
    signals: dict[str, list[str]] = {}
    generated_by: DnaSource = DnaSource.DETERMINISTIC_BASELINE
