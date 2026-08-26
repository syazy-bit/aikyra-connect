"""Schemas for the Phase 4B institution matching endpoint."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from app.core import taxonomy
from app.models.institution import InstitutionVerificationStatus
from app.schemas.institution import DomainRef


class ScoreFactor(BaseModel):
    """One scored factor: points earned, maximum possible, and the matched
    evidence behind the points."""

    points: int
    max: int
    detail: list[str] = []


class MatchedInstitution(BaseModel):
    """Institution summary embedded in a recommendation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    institution_type: str
    location: str
    website: str | None
    domains: list[str]
    verification_status: InstitutionVerificationStatus

    @computed_field  # type: ignore[prop-decorator]
    @property
    def domain_labels(self) -> list[DomainRef]:
        refs = []
        for key in self.domains:
            label = taxonomy.domain_label(key)
            refs.append(DomainRef(key=key, label=label or key))
        return refs


class MatchItem(BaseModel):
    institution: MatchedInstitution
    score: int
    score_breakdown: dict[str, ScoreFactor]
    reasons: list[str]


class MatchListResponse(BaseModel):
    challenge_id: UUID
    dna_eligible: bool
    pool_size: int
    items: list[MatchItem]
    total: int
    skip: int
    limit: int
