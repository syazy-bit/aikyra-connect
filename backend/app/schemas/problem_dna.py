from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from app.core import taxonomy
from app.models.problem_dna import DnaSource, DnaValidationStatus, UrgencyLevel


class ProblemDnaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    primary_domain: str | None
    secondary_domains: list[str]
    subdomain: str | None
    problem_type: str | None
    geographic_context: str | None
    urgency: UrgencyLevel
    affected_stakeholders: list[str]
    keywords: list[str]
    required_expertise: list[str]
    potential_solution_areas: list[str]
    confidence_score: float | None
    signals: dict[str, list[str]]
    generated_by: DnaSource
    analyzer_version: str
    validation_status: DnaValidationStatus
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def primary_domain_label(self) -> str | None:
        return taxonomy.domain_label(self.primary_domain)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def secondary_domain_labels(self) -> list[str]:
        return [taxonomy.domain_label(key) for key in self.secondary_domains]


class AnalyzeResponse(BaseModel):
    """Result of running analysis on a challenge."""

    dna: ProblemDnaResponse
    regenerated: bool
