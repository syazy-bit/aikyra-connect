"""Admin dashboard API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_review_institutions, require_review_problems
from app.models.user import User
from app.schemas.admin import (
    AdminChallengeDetailResponse,
    AdminChallengeListItem,
    AdminInstitutionListQuery,
    AdminInstitutionListResponse,
    AdminOverviewResponse,
    ChallengeStatusTransitionRequest,
    DNAValidationRequest,
)
from app.services.admin_challenge_service import AdminChallengeService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_admin_challenge_service(db: Session = Depends(get_db)) -> AdminChallengeService:
    return AdminChallengeService(db)


@router.get("/overview", response_model=AdminOverviewResponse)
def admin_overview(
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
) -> AdminOverviewResponse:
    """Get aggregated counts for admin overview dashboard.
    
    Requires either can_review_problems or can_review_institutions capability.
    """
    return service.get_overview()


# --- Challenge Review Endpoints ---

@router.get("/challenges", response_model=list[AdminChallengeListItem])
def admin_list_challenges(
    status: str | None = Query(default=None),
    dna_validation_status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
) -> list[AdminChallengeListItem]:
    """List challenges for admin review with optional filters."""
    from app.models.challenge import ChallengeStatus
    from app.models.problem_dna import DnaValidationStatus
    
    status_enum = ChallengeStatus(status) if status else None
    dna_status_enum = DnaValidationStatus(dna_validation_status) if dna_validation_status else None
    
    items, _ = service.list_challenges_for_review(
        status=status_enum,
        dna_validation_status=dna_status_enum,
        skip=skip,
        limit=limit,
    )
    return items


@router.get("/challenges/{challenge_id}", response_model=AdminChallengeDetailResponse)
def admin_get_challenge(
    challenge_id: UUID,
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
) -> AdminChallengeDetailResponse:
    """Get full challenge detail for admin review."""
    return service.get_challenge_for_review(challenge_id)


@router.patch("/challenges/{challenge_id}/status", response_model=AdminChallengeDetailResponse)
def admin_transition_challenge_status(
    challenge_id: UUID,
    request: ChallengeStatusTransitionRequest,
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
) -> AdminChallengeDetailResponse:
    """Transition challenge status (SUBMITTED -> UNDER_REVIEW -> VALIDATED/REJECTED)."""
    challenge = service.transition_challenge_status(
        challenge_id=challenge_id,
        request=request,
        reviewer_id=current_user.id,
    )
    # Return updated challenge with DNA
    return service.get_challenge_for_review(challenge_id)


@router.post("/challenges/{challenge_id}/dna/validate", response_model=AdminChallengeDetailResponse)
def admin_validate_dna(
    challenge_id: UUID,
    request: DNAValidationRequest,
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
) -> AdminChallengeDetailResponse:
    """Validate or update Problem DNA."""
    service.validate_dna(
        challenge_id=challenge_id,
        request=request,
        reviewer_id=current_user.id,
    )
    # Return updated challenge with DNA
    return service.get_challenge_for_review(challenge_id)


@router.get("/challenges/{challenge_id}/audit")
def admin_get_challenge_audit(
    challenge_id: UUID,
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_problems),
):
    """Get audit history for a challenge."""
    from app.schemas.admin import AdminChallengeDetailResponse
    from app.models.challenge_review_audit import ChallengeReviewAudit
    
    audit_records = service.get_challenge_audit(challenge_id)
    
    return [
        {
            "id": str(record.id),
            "action": record.action,
            "previous_status": record.previous_status.value if record.previous_status else None,
            "new_status": record.new_status.value if record.new_status else None,
            "previous_dna_validation_status": record.previous_dna_validation_status.value if record.previous_dna_validation_status else None,
            "new_dna_validation_status": record.new_dna_validation_status.value if record.new_dna_validation_status else None,
            "note": record.note,
            "reviewer_id": str(record.reviewer_id),
            "created_at": record.created_at.isoformat(),
        }
        for record in audit_records
    ]


# --- Institution Review Endpoints ---

@router.get("/institutions", response_model=AdminInstitutionListResponse)
def admin_list_institutions(
    query: Annotated[AdminInstitutionListQuery, Query()],
    service: AdminChallengeService = Depends(get_admin_challenge_service),
    current_user: User = Depends(require_review_institutions),
) -> AdminInstitutionListResponse:
    """List institutions for admin review with filters."""
    return service.list_institutions_for_review(query)


# The verification endpoint already exists at /api/institutions/{id}/verification
# and is protected by require_platform_reviewer. It can be used by admins with
# can_review_institutions capability as well if we want to allow both.
# For now, we keep the existing endpoint unchanged for backward compatibility.