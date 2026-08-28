from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_team_lead,
    require_team_member,
    require_team_viewer,
)
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamListQuery,
    TeamListResponse,
    TeamMembersResponse,
    TeamMembershipResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.team_service import TeamService

router = APIRouter(prefix="/api/teams", tags=["teams"])


def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    return TeamService(db)


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Create a team for a challenge.

    Requires an ACTIVE institution membership with a role that permits
    team creation (owner, representative, faculty, or student).
    The authenticated user automatically becomes the team lead.
    """
    team = service.create_team(
        institution_id=payload.institution_id,
        challenge_id=payload.challenge_id,
        name=payload.name,
        description=payload.description,
        creator_user_id=current_user.id,
    )
    return TeamResponse.model_validate(team)


@router.get("", response_model=TeamListResponse)
def list_teams(
    query: Annotated[TeamListQuery, Query()],
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamListResponse:
    """List teams with optional filters.

    The authenticated user can only see teams from institutions where
    they have an active institution membership, or teams they belong to.
    Access is resolved from the database at request time — institution_id
    from the query string only narrows, never widens, discovery.
    """
    teams, total = service.list_visible_teams(
        user_id=current_user.id,
        institution_id=query.institution_id,
        challenge_id=query.challenge_id,
        status=query.status,
        skip=query.skip,
        limit=query.limit,
    )
    items = [TeamResponse.model_validate(t) for t in teams]
    return TeamListResponse(items=items, total=total, skip=query.skip, limit=query.limit)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: UUID,
    current_user: User = Depends(require_team_viewer),
    service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Get team details.

    Requires an ACTIVE team membership, or being an owner/representative
    of the team's institution.
    """
    team = service.get_team(team_id)
    return TeamResponse.model_validate(team)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    current_user: User = Depends(require_team_lead),
    service: TeamService = Depends(get_team_service),
) -> TeamResponse:
    """Update team name and/or description.

    Only the team's active lead can update the team.
    """
    team = service.update_team(
        team_id=team_id,
        name=payload.name,
        description=payload.description,
    )
    return TeamResponse.model_validate(team)


@router.get("/{team_id}/members", response_model=TeamMembersResponse)
def list_team_members(
    team_id: UUID,
    current_user: User = Depends(require_team_member),
    service: TeamService = Depends(get_team_service),
) -> TeamMembersResponse:
    """List team members.

    Requires an ACTIVE team membership.
    """
    members = service.list_members(team_id)
    items = [TeamMembershipResponse.model_validate(m) for m in members]
    return TeamMembersResponse(items=items, total=len(items))