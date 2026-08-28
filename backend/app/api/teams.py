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
    TeamInviteCreate,
    TeamListQuery,
    TeamListResponse,
    TeamMembersResponse,
    TeamMembershipResponse,
    TeamResponse,
    TeamUpdate,
    TransferLeadershipRequest,
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


@router.get("/invitations/me", response_model=TeamMembersResponse)
def my_invitations(
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamMembersResponse:
    """List the authenticated user's pending team invitations.

    No team membership is required — pending invitations are the discoverable
    entry point for an invitee who has not yet joined the team. Results are
    scoped to the authenticated user only.
    """
    items = [
        TeamMembershipResponse.model_validate(m)
        for m in service.list_my_invitations(current_user.id)
    ]
    return TeamMembersResponse(items=items, total=len(items))


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


@router.post(
    "/{team_id}/invitations",
    response_model=TeamMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_to_team(
    team_id: UUID,
    payload: TeamInviteCreate,
    current_user: User = Depends(require_team_lead),
    service: TeamService = Depends(get_team_service),
) -> TeamMembershipResponse:
    """Invite a user to the team.

    Only the active team lead may invite. The invitee must already hold an
    ACTIVE faculty or student institution membership at the team's
    institution (resolved from the database, never the client).
    """
    membership = service.invite_member(
        team_id=team_id,
        invitee_user_id=payload.user_id,
        inviter_user_id=current_user.id,
    )
    return TeamMembershipResponse.model_validate(membership)


@router.post(
    "/{team_id}/invitations/{membership_id}/accept",
    response_model=TeamMembershipResponse,
)
def accept_invitation(
    team_id: UUID,
    membership_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamMembershipResponse:
    """Accept a pending team invitation.

    Only the invited user may accept. The invitee's active faculty/student
    institution membership is re-validated at accept time, and joined_at is
    set server-side.
    """
    membership = service.accept_invitation(
        team_id=team_id,
        membership_id=membership_id,
        user_id=current_user.id,
    )
    return TeamMembershipResponse.model_validate(membership)


@router.post(
    "/{team_id}/invitations/{membership_id}/decline",
    response_model=TeamMembershipResponse,
)
def decline_invitation(
    team_id: UUID,
    membership_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamMembershipResponse:
    """Decline a pending team invitation (removes the invitation row).

    Only the invited user may decline.
    """
    membership = service.decline_invitation(
        team_id=team_id,
        membership_id=membership_id,
        user_id=current_user.id,
    )
    return TeamMembershipResponse.model_validate(membership)


@router.post("/{team_id}/leave", response_model=TeamMembershipResponse)
def leave_team(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamMembershipResponse:
    """Leave a team as an active non-lead member.

    The active lead cannot leave until leadership is transferred (409).
    Leaving removes the membership row.
    """
    membership = service.leave_team(team_id=team_id, user_id=current_user.id)
    return TeamMembershipResponse.model_validate(membership)


@router.post("/{team_id}/leadership", response_model=TeamMembershipResponse)
def transfer_leadership(
    team_id: UUID,
    payload: TransferLeadershipRequest,
    current_user: User = Depends(require_team_lead),
    service: TeamService = Depends(get_team_service),
) -> TeamMembershipResponse:
    """Transfer team leadership to another active member.

    Only the current active lead may transfer. The transfer demotes the
    current lead and promotes the target atomically in one transaction;
    the partial unique index guarantees exactly one active lead per team.
    """
    membership = service.transfer_leadership(
        team_id=team_id,
        current_lead_id=current_user.id,
        new_lead_id=payload.new_lead_user_id,
    )
    return TeamMembershipResponse.model_validate(membership)