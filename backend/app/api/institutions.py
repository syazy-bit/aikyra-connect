from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.dependencies.auth import get_current_user, require_owner_or_rep
from app.models.user import User
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListQuery,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdate,
    MembershipResponse,
)
from app.services.institution_service import InstitutionService

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


def get_institution_service(db: Session = Depends(get_db)) -> InstitutionService:
    return InstitutionService(db)


@router.post(
    "", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED
)
def register_institution(
    payload: InstitutionCreate,
    current_user: User = Depends(get_current_user),
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Register an institution.

    Requires authentication. The authenticated user becomes the owner.
    Every registration starts `active` + `unverified` (human-entered data).
    Verification is performed by reviewers in a later phase.
    """
    return service.to_response(
        service.create_institution(payload, owner_user_id=current_user.id)
    )


@router.get("", response_model=InstitutionListResponse)
def list_institutions(
    query: Annotated[InstitutionListQuery, Query()],
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionListResponse:
    """Institution listing foundation: search, type/domain filters, sorting,
    pagination."""
    return service.list_institutions(query)


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: UUID,
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Full institution profile including capability data."""
    return service.to_response(service.get_institution(institution_id))


@router.get("/{institution_id}/membership", response_model=MembershipResponse)
def get_membership(
    institution_id: UUID,
    current_user: User = Depends(get_current_user),
    service: InstitutionService = Depends(get_institution_service),
) -> MembershipResponse:
    """Get the authenticated user's membership status for an institution.

    Returns the user's own membership information. Does not leak
    membership data for other users.
    """
    result = service.get_membership(current_user.id, institution_id)
    if result is None:
        return MembershipResponse(is_member=False)
    return MembershipResponse(**result)


@router.patch("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: UUID,
    payload: InstitutionUpdate,
    current_user: User = Depends(require_owner_or_rep),
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Partial profile/capability update (replace-whole semantics for the
    capabilities object).

    Requires authentication plus an active owner or representative
    membership for the institution. Verification/lifecycle fields are
    intentionally excluded from this payload.
    """
    return service.to_response(service.update_institution(institution_id, payload))
