"""Schemas for Phase 5 team foundation."""

from datetime import datetime
import enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamStatus(str, enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class TeamRole(str, enum.Enum):
    LEAD = "lead"
    MEMBER = "member"


class TeamMembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class TeamCreate(BaseModel):
    """Payload for creating a new team."""

    model_config = ConfigDict(extra="forbid")

    institution_id: UUID
    challenge_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class TeamUpdate(BaseModel):
    """Payload for updating a team.

    Only name and description are editable. All other fields
    are server-controlled.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class TeamResponse(BaseModel):
    """Team response with full details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    challenge_id: UUID
    name: str
    description: str | None
    status: TeamStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TeamListItem(BaseModel):
    """Trimmed projection for listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    challenge_id: UUID
    name: str
    status: TeamStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    items: list[TeamListItem]
    total: int
    skip: int
    limit: int


class TeamListQuery(BaseModel):
    """Validated listing query parameters."""

    model_config = ConfigDict(str_strip_whitespace=True)

    institution_id: UUID | None = None
    challenge_id: UUID | None = None
    status: TeamStatus | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class TeamMembershipResponse(BaseModel):
    """Response for a team member."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    role: TeamRole
    status: TeamMembershipStatus
    invited_by: UUID | None
    joined_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TeamMembersResponse(BaseModel):
    items: list[TeamMembershipResponse]
    total: int


class TeamInviteCreate(BaseModel):
    """Payload for inviting a user to a team.

    Only the invitee identity is client-supplied. The membership role,
    status, invited_by and joined_at fields are all server-controlled.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class TransferLeadershipRequest(BaseModel):
    """Payload for transferring team leadership to another active member."""

    model_config = ConfigDict(extra="forbid")

    new_lead_user_id: UUID