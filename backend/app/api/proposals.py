from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.proposal import (
    ProposalCreate,
    ProposalListQuery,
    ProposalListResponse,
    ProposalResponse,
    ProposalUpdate,
)
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


def get_proposal_service(db: Session = Depends(get_db)) -> ProposalService:
    return ProposalService(db)


@router.post(
    "",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_proposal(
    payload: ProposalCreate,
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalResponse:
    """Create a draft proposal for a team and challenge.

    Requires an ACTIVE team membership (resolved from the database). The
    challenge must match the team's challenge, otherwise a 409 is returned.
    Proposals are always created in the draft state.
    """
    proposal = service.create_proposal(
        team_id=payload.team_id,
        challenge_id=payload.challenge_id,
        title=payload.title,
        summary=payload.summary,
        approach=payload.approach,
        resources_needed=payload.resources_needed,
        timeline=payload.timeline,
        creator_user_id=current_user.id,
    )
    return ProposalResponse.model_validate(proposal)


@router.get("", response_model=ProposalListResponse)
def list_proposals(
    query: Annotated[ProposalListQuery, Query()],
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalListResponse:
    """List proposals visible to the authenticated user.

    A proposal is visible only to ACTIVE team members or ACTIVE institution
    owners/representatives of the team's institution. team_id and status from
    the query string only narrow, never widen, discovery.
    """
    proposals, total = service.list_proposals(
        user_id=current_user.id,
        team_id=query.team_id,
        status=query.status,
        skip=query.skip,
        limit=query.limit,
    )
    items = [ProposalResponse.model_validate(p) for p in proposals]
    return ProposalListResponse(
        items=items, total=total, skip=query.skip, limit=query.limit
    )


@router.get("/{proposal_id}", response_model=ProposalResponse)
def get_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalResponse:
    """Get a proposal by id.

    The caller must be an ACTIVE team member or an ACTIVE institution
    owner/representative of the team's institution.
    """
    proposal = service.get_proposal(proposal_id, user_id=current_user.id)
    return ProposalResponse.model_validate(proposal)


@router.patch("/{proposal_id}", response_model=ProposalResponse)
def update_proposal(
    proposal_id: UUID,
    payload: ProposalUpdate,
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalResponse:
    """Edit a draft proposal.

    Requires an ACTIVE team membership. Only draft proposals are editable;
    editing a submitted or withdrawn proposal returns a 409.
    """
    proposal = service.update_proposal(
        proposal_id=proposal_id,
        user_id=current_user.id,
        fields=payload.model_dump(exclude_unset=True),
    )
    return ProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/submit", response_model=ProposalResponse)
def submit_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalResponse:
    """Submit a draft proposal (draft -> submitted).

    Only the team's active lead may submit. submitted_at is set server-side.
    """
    proposal = service.submit_proposal(
        proposal_id=proposal_id, lead_user_id=current_user.id
    )
    return ProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/withdraw", response_model=ProposalResponse)
def withdraw_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProposalService = Depends(get_proposal_service),
) -> ProposalResponse:
    """Withdraw a proposal (draft|submitted -> withdrawn).

    Only the team's active lead may withdraw. Withdrawal is terminal in CP3 —
    the (team, challenge) proposal slot stays permanently consumed.
    """
    proposal = service.withdraw_proposal(
        proposal_id=proposal_id, lead_user_id=current_user.id
    )
    return ProposalResponse.model_validate(proposal)