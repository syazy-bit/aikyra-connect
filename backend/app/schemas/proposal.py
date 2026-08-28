"""Schemas for Phase 5 solution proposals (CP3 core)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.proposal import ProposalStatus


class ProposalCreate(BaseModel):
    """Payload for creating a draft proposal.

    Only team/challenge identity and proposal content are client-supplied.
    status, submitted_at, reviewed_at, reviewed_by, review_note, created_at,
    updated_at and created_by are server-controlled and rejected here.
    """

    model_config = ConfigDict(extra="forbid")

    team_id: UUID
    challenge_id: UUID
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=20000)
    approach: str | None = Field(default=None, max_length=20000)
    resources_needed: str | None = Field(default=None, max_length=20000)
    timeline: str | None = Field(default=None, max_length=20000)

    @field_validator("title", "summary")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("approach", "resources_needed", "timeline")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProposalUpdate(BaseModel):
    """Payload for editing a draft proposal.

    team_id and challenge_id are immutable after creation. status and all
    lifecycle fields are never client-controlled. Optional text fields may be
    cleared by sending explicit null.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, min_length=1, max_length=20000)
    approach: str | None = Field(default=None, max_length=20000)
    resources_needed: str | None = Field(default=None, max_length=20000)
    timeline: str | None = Field(default=None, max_length=20000)

    @field_validator("title", "summary")
    @classmethod
    def _strip_required(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("approach", "resources_needed", "timeline")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProposalResponse(BaseModel):
    """Full proposal projection including CP4 review fields (null until then)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    challenge_id: UUID
    title: str
    summary: str
    approach: str | None
    resources_needed: str | None
    timeline: str | None
    status: ProposalStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class ProposalListItem(BaseModel):
    """Trimmed projection for listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    challenge_id: UUID
    title: str
    status: ProposalStatus
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProposalListResponse(BaseModel):
    items: list[ProposalListItem]
    total: int
    skip: int
    limit: int


class ProposalListQuery(BaseModel):
    """Validated listing query parameters.

    team_id and status only narrow discovery; the visibility predicate is
    always applied so a caller can never widen their own access.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    team_id: UUID | None = None
    status: ProposalStatus | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)