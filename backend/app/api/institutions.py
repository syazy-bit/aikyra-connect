from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.dependencies.auth import get_current_user, require_institution_admin_or_rep
from app.models.user import User
from app.repositories.institution_repository import InstitutionRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListQuery,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdate,
    MembershipResponse,
    VerificationAction,
    VerificationRequest,
    VerificationResponse,
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

    Requires authentication. The authenticated user becomes the institution's
    first institution_admin. Every registration starts `active` + `unverified`
    (human-entered data). Verification is performed by platform reviewers.
    """
    return service.to_response(
        service.create_institution(payload, institution_admin_user_id=current_user.id)
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
    current_user: User = Depends(require_institution_admin_or_rep),
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Partial profile/capability update (replace-whole semantics for the
    capabilities object).

    Requires authentication plus an active institution_admin or representative
    membership for the institution. Verification/lifecycle fields are
    intentionally excluded from this payload.
    """
    return service.to_response(service.update_institution(institution_id, payload))


_REVIEWER_ACTIONS = {
    VerificationAction.VERIFY,
    VerificationAction.REJECT,
    VerificationAction.SUSPEND,
    VerificationAction.REINSTATE,
}

_INSTITUTION_ADMIN_ACTIONS = {
    VerificationAction.SUBMIT_FOR_REVIEW,
    VerificationAction.RESUBMIT,
}


@router.patch(
    "/{institution_id}/verification",
    response_model=VerificationResponse,
)
def update_verification(
    institution_id: UUID,
    payload: VerificationRequest,
    current_user: User = Depends(get_current_user),
    service: InstitutionService = Depends(get_institution_service),
) -> VerificationResponse:
    """Verification workflow endpoint.

    Enforces a server-side state machine. Authorization is resolved from
    the database-backed membership system.

    Institution admin/representative actions: submit_for_review, resubmit.
    Platform reviewer actions: verify, reject, suspend, reinstate.
    """
    membership_repo = MembershipRepository(service.db)

    institution_repo = InstitutionRepository(service.db)
    if institution_repo.get_by_id(institution_id) is None:
        raise NotFoundError("Institution", institution_id)

    if payload.action in _REVIEWER_ACTIONS:
        # Platform reviewer authorization - no institution membership required
        if not current_user.is_platform_reviewer:
            raise ForbiddenError(
                "You do not have platform reviewer permissions."
            )
    elif payload.action in _INSTITUTION_ADMIN_ACTIONS:
        if not membership_repo.has_role(
            current_user.id, institution_id, ("institution_admin", "representative")
        ):
            raise ForbiddenError(
                "You do not have permission to modify this institution."
            )

    action = payload.action
    note = payload.note

    if action == VerificationAction.SUBMIT_FOR_REVIEW:
        institution = service.submit_for_review(institution_id)
    elif action == VerificationAction.VERIFY:
        institution = service.verify_institution(
            institution_id, reviewer_user_id=current_user.id, note=note
        )
    elif action == VerificationAction.REJECT:
        institution = service.reject_institution(
            institution_id, reviewer_user_id=current_user.id, note=note
        )
    elif action == VerificationAction.RESUBMIT:
        institution = service.resubmit(institution_id)
    elif action == VerificationAction.SUSPEND:
        institution = service.suspend_institution(
            institution_id, reviewer_user_id=current_user.id, note=note
        )
    elif action == VerificationAction.REINSTATE:
        institution = service.reinstate_institution(
            institution_id, reviewer_user_id=current_user.id, note=note
        )

    return VerificationResponse(
        id=institution.id,
        verification_status=institution.verification_status,
        verification_note=institution.verification_note,
        verified_at=institution.verified_at,
        verified_by=institution.verified_by,
        updated_at=institution.updated_at,
    )
