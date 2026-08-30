"""Schemas for the Phase 3 discovery experience."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.core import taxonomy
from app.models.challenge import ChallengeStatus
from app.models.problem_dna import DnaValidationStatus, UrgencyLevel


class SortOption(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    URGENT = "urgency"
    RELEVANCE = "relevance"


class DiscoveryQuery(BaseModel):
    """Validated discovery query parameters (bound via FastAPI Query model).

    Multi-value params accept either repeated keys (`domains=a&domains=b`)
    or comma-separated values (`domains=a,b`).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str | None = Field(default=None, max_length=200)
    domains: list[str] = Field(default_factory=list)
    urgencies: list[UrgencyLevel] = Field(default_factory=list)
    location: str | None = Field(default=None, max_length=200)
    has_dna: bool | None = None
    sort: SortOption = SortOption.NEWEST
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _validate_sort_combination(self):
        if self.sort == SortOption.RELEVANCE and not self.q:
            raise ValueError("'sort=relevance' requires a search query ('q')")
        return self

    @staticmethod
    def _split_csv(values: list[str]) -> list[str]:
        return [v.strip() for raw in values for v in raw.split(",") if v.strip()]

    @field_validator("domains")
    @classmethod
    def _validate_domains(cls, value: list[str]) -> list[str]:
        slugs = cls._split_csv(value)
        for slug in slugs:
            if taxonomy.get_domain(slug) is None:
                raise ValueError(f"unknown domain '{slug}'")
        return list(dict.fromkeys(slugs))

    @field_validator("urgencies", mode="before")
    @classmethod
    def _validate_urgencies(cls, value):
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return value
        return cls._split_csv([str(v) for v in value])

    @field_validator("q", "location")
    @classmethod
    def _strip_or_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProblemDnaSummary(BaseModel):
    """Lightweight DNA projection embedded in discovery results — no N+1."""

    model_config = ConfigDict(from_attributes=True)

    primary_domain: str | None
    subdomain: str | None
    problem_type: str | None
    urgency: UrgencyLevel
    confidence_score: float | None
    validation_status: DnaValidationStatus

    @computed_field  # type: ignore[prop-decorator]
    @property
    def primary_domain_label(self) -> str | None:
        return taxonomy.domain_label(self.primary_domain)


class ChallengeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str
    status: ChallengeStatus
    created_at: datetime
    updated_at: datetime
    dna: ProblemDnaSummary | None = None
    has_image: bool = False


class ChallengeListResponse(BaseModel):
    items: list[ChallengeListItem]
    total: int
    skip: int
    limit: int


class ChallengeDetailResponse(ChallengeListItem):
    """Single challenge with its embedded DNA summary (or null if unanalyzed)."""
