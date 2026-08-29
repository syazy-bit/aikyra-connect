"""Schemas for approved-solution projects and public listing."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import ProjectStatus


class OrganizationRef(BaseModel):
    id: UUID
    name: str


class ProjectOfferRef(BaseModel):
    id: UUID
    organization: OrganizationRef
    support_type: str
    message: str | None
    status: str
    created_at: datetime


class ProjectListItem(BaseModel):
    """Trimmed public projection for the approved-solutions board."""

    id: UUID
    title: str
    team_id: UUID
    status: ProjectStatus
    institution_name: str
    team_name: str
    challenge_title: str
    offer_count: int
    created_at: datetime


class ProjectDetailResponse(BaseModel):
    """Full public projection including the project's support offers."""

    id: UUID
    title: str
    status: ProjectStatus
    institution_name: str
    team_name: str
    challenge_title: str
    offers: list[ProjectOfferRef]
    created_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    total: int
    skip: int
    limit: int


class ProjectListQuery(BaseModel):
    """Validated public listing query parameters."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: ProjectStatus | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
