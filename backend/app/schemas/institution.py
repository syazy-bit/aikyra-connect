"""Schemas for Phase 4A institution foundation."""

from datetime import datetime
import enum
import re
from urllib.parse import urlparse
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
from app.models.institution import (
    InstitutionStatus,
    InstitutionType,
    InstitutionVerificationStatus,
)


def _strip_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty or whitespace")
    return value


CAPABILITY_ITEM_MAX_LENGTH = 200


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class SortOption(str, enum.Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    RELEVANCE = "relevance"


class CapabilityProfile(BaseModel):
    """Human-entered institutional capability profile.

    Fixed additive sections; every section is an array of non-empty strings.
    Unknown sections are rejected so typos cannot silently drop capability
    data that the future matching engine depends on. All data is
    human-entered in Phase 4A — no AI-derived content exists here.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    departments: list[str] = Field(default_factory=list, max_length=20)
    disciplines: list[str] = Field(default_factory=list, max_length=30)
    expertise: list[str] = Field(default_factory=list, max_length=40)
    research_areas: list[str] = Field(default_factory=list, max_length=30)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    facilities: list[str] = Field(default_factory=list, max_length=30)
    innovation_support: list[str] = Field(default_factory=list, max_length=10)
    prototyping: list[str] = Field(default_factory=list, max_length=15)
    project_experience: list[str] = Field(default_factory=list, max_length=20)
    collaboration_modes: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("*", mode="before")
    @classmethod
    def _clean_items(cls, value):
        if not isinstance(value, list):
            return value
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("capability items must be strings")
            text = item.strip()
            if not text:
                continue
            if len(text) > CAPABILITY_ITEM_MAX_LENGTH:
                raise ValueError(
                    "capability items must be at most "
                    f"{CAPABILITY_ITEM_MAX_LENGTH} characters"
                )
            cleaned.append(text)
        return _dedupe_preserving_order(cleaned)


class InstitutionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=250)
    institution_type: InstitutionType
    description: str | None = Field(default=None, max_length=5000)
    location: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=254)
    domains: list[str] = Field(default_factory=list)
    capabilities: CapabilityProfile = Field(default_factory=CapabilityProfile)

    @field_validator("name", "location")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        return _strip_non_empty(value)

    @field_validator("description")
    @classmethod
    def _validate_optional_description(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @field_validator("website")
    @classmethod
    def _validate_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or whitespace")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be a valid absolute http(s) URL")
        return value

    @field_validator("contact_email")
    @classmethod
    def _validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or whitespace")
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.fullmatch(pattern, value):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("domains", mode="before")
    @classmethod
    def _validate_domains(cls, value):
        if value is None:
            return []
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError("domains must be a list of taxonomy slugs")
        slugs = [slug.strip() for slug in value]
        for slug in slugs:
            if taxonomy.get_domain(slug) is None:
                raise ValueError(f"unknown domain '{slug}'")
        cleaned = _dedupe_preserving_order([s for s in slugs if s])
        if len(cleaned) > len(taxonomy.all_domains()):
            raise ValueError(
                f"at most {len(taxonomy.all_domains())} domains are allowed"
            )
        return cleaned


class InstitutionUpdate(BaseModel):
    """Partial update payload.

    Verification/lifecycle fields (`status`, `verification_status`,
    `verification_note`, `verified_at`, `verified_by`) are intentionally
    excluded — they are trust/workflow fields owned by reviewers with roles
    in a later phase.

    Unknown fields are rejected to prevent mass-assignment of trust fields.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=250)
    institution_type: InstitutionType | None = None
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=254)
    domains: list[str] | None = None
    capabilities: CapabilityProfile | None = None

    @field_validator("name", "location")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def _validate_optional_description(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @field_validator("website")
    @classmethod
    def _validate_optional_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return InstitutionCreate._validate_website(value)

    @field_validator("contact_email")
    @classmethod
    def _validate_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return InstitutionCreate._validate_contact_email(value)

    @field_validator("domains", mode="before")
    @classmethod
    def _validate_optional_domains(cls, value):
        if value is None:
            return None
        return InstitutionCreate._validate_domains(value)


class DomainRef(BaseModel):
    key: str
    label: str


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    institution_type: InstitutionType
    description: str | None
    location: str
    website: str | None
    contact_email: str | None
    domains: list[str]
    capabilities: dict[str, list[str]]
    status: InstitutionStatus
    verification_status: InstitutionVerificationStatus
    verification_note: str | None
    verified_at: datetime | None
    verified_by: UUID | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def domain_labels(self) -> list[DomainRef]:
        refs = []
        for key in self.domains:
            label = taxonomy.domain_label(key)
            refs.append(DomainRef(key=key, label=label or key))
        return refs


class InstitutionListItem(BaseModel):
    """Trimmed projection for listing — no capability payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    institution_type: InstitutionType
    location: str
    domains: list[str]
    status: InstitutionStatus
    verification_status: InstitutionVerificationStatus
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def domain_labels(self) -> list[DomainRef]:
        refs = []
        for key in self.domains:
            label = taxonomy.domain_label(key)
            refs.append(DomainRef(key=key, label=label or key))
        return refs


class InstitutionListResponse(BaseModel):
    items: list[InstitutionListItem]
    total: int
    skip: int
    limit: int


class InstitutionListQuery(BaseModel):
    """Validated listing query parameters (bound via FastAPI Query model).

    Multi-value params accept either repeated keys (`domains=a&domains=b`)
    or comma-separated values (`domains=a,b`) — same convention as discovery.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str | None = Field(default=None, max_length=200)
    types: list[InstitutionType] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
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

    @field_validator("types", mode="before")
    @classmethod
    def _split_types(cls, value):
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return value
        return cls._split_csv([str(v) for v in value])

    @field_validator("domains")
    @classmethod
    def _validate_domains(cls, value: list[str]) -> list[str]:
        slugs = cls._split_csv(value)
        for slug in slugs:
            if taxonomy.get_domain(slug) is None:
                raise ValueError(f"unknown domain '{slug}'")
        return _dedupe_preserving_order(slugs)

    @field_validator("q")
    @classmethod
    def _strip_or_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class MembershipResponse(BaseModel):
    """Response for the authenticated user's membership status on an institution."""

    is_member: bool
    role: str | None = None
    membership_status: str | None = None
