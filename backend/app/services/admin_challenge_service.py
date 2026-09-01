"""Admin challenge review service."""

from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.challenge import Challenge, ChallengeStatus
from app.models.challenge_review_audit import ChallengeReviewAudit
from app.models.institution import Institution, InstitutionVerificationStatus
from app.models.problem_dna import DnaValidationStatus, ProblemDna
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.discovery_repository import DiscoveryRepository
from app.repositories.institution_repository import InstitutionRepository
from app.schemas.admin import (
    AdminChallengeDetailResponse,
    AdminChallengeListItem,
    AdminInstitutionListItem,
    AdminInstitutionListQuery,
    AdminInstitutionListResponse,
    AdminOverviewResponse,
    AdminProblemDnaDetail,
    AdminProblemDnaSummary,
    ChallengeStatusTransitionRequest,
    DNAValidationRequest,
)


# Valid challenge status transitions
VALID_STATUS_TRANSITIONS = {
    ChallengeStatus.SUBMITTED: {ChallengeStatus.UNDER_REVIEW},
    ChallengeStatus.UNDER_REVIEW: {ChallengeStatus.VALIDATED, ChallengeStatus.REJECTED},
    # VALIDATED and REJECTED are terminal states
}


class AdminChallengeService:
    """Business logic for admin challenge review."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.challenge_repo = ChallengeRepository(db)
        self.discovery_repo = DiscoveryRepository(db)
        self.institution_repo = InstitutionRepository(db)

    # --- Overview ---------------------------------------------------------

    def get_overview(self) -> AdminOverviewResponse:
        """Get aggregated counts for admin overview."""
        # Problems awaiting review (SUBMITTED + UNDER_REVIEW)
        problems_awaiting = self.db.execute(
            select(Challenge).where(Challenge.status.in_([
                ChallengeStatus.SUBMITTED, ChallengeStatus.UNDER_REVIEW
            ]))
        ).scalars().all()
        
        # DNA needing validation (NEEDS_REVIEW + PENDING_VALIDATION)
        dna_needing = self.db.execute(
            select(ProblemDna).where(ProblemDna.validation_status.in_([
                DnaValidationStatus.NEEDS_REVIEW, DnaValidationStatus.PENDING_VALIDATION
            ]))
        ).scalars().all()

        # Institutions pending verification
        institutions_pending = self.db.execute(
            select(Institution).where(
                Institution.verification_status == InstitutionVerificationStatus.PENDING_REVIEW
            )
        ).scalars().all()

        # Verified institutions
        verified_institutions = self.db.execute(
            select(Institution).where(
                Institution.verification_status == InstitutionVerificationStatus.VERIFIED
            )
        ).scalars().all()

        return AdminOverviewResponse(
            problems_awaiting_review=len(problems_awaiting),
            dna_needing_validation=len(dna_needing),
            institutions_pending_verification=len(institutions_pending),
            verified_institutions=len(verified_institutions),
        )

    # --- Challenge Review Queue -------------------------------------------

    def list_challenges_for_review(
        self,
        status: ChallengeStatus | None = None,
        dna_validation_status: DnaValidationStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AdminChallengeListItem], int]:
        """List challenges for admin review with filters."""
        # Build query with DNA join
        query = (
            select(Challenge, ProblemDna)
            .outerjoin(ProblemDna, ProblemDna.challenge_id == Challenge.id)
            .order_by(Challenge.created_at.desc())
        )

        if status:
            query = query.where(Challenge.status == status)
        if dna_validation_status:
            query = query.where(ProblemDna.validation_status == dna_validation_status)

        # Get total count
        count_query = query.with_only_columns(sa.func.count()).order_by(None)
        total = self.db.execute(count_query).scalar() or 0

        # Apply pagination
        query = query.offset(skip).limit(limit)
        rows = self.db.execute(query).all()

        items = []
        for challenge, dna in rows:
            dna_summary = None
            if dna:
                dna_summary = AdminProblemDnaSummary(
                    primary_domain=dna.primary_domain,
                    urgency=dna.urgency,
                    confidence_score=float(dna.confidence_score) if dna.confidence_score else None,
                    validation_status=dna.validation_status,
                )
            items.append(AdminChallengeListItem(
                id=challenge.id,
                title=challenge.title,
                location=challenge.location,
                status=challenge.status,
                created_at=challenge.created_at,
                updated_at=challenge.updated_at,
                dna=dna_summary,
            ))

        return items, total

    def get_challenge_for_review(self, challenge_id: UUID) -> AdminChallengeDetailResponse:
        """Get full challenge detail for admin review."""
        challenge, dna = self._get_challenge_with_dna(challenge_id)
        
        dna_detail = None
        if dna:
            dna_detail = AdminProblemDnaDetail(
                id=dna.id,
                challenge_id=dna.challenge_id,
                primary_domain=dna.primary_domain,
                secondary_domains=dna.secondary_domains,
                subdomain=dna.subdomain,
                problem_type=dna.problem_type,
                geographic_context=dna.geographic_context,
                urgency=dna.urgency,
                affected_stakeholders=dna.affected_stakeholders,
                keywords=dna.keywords,
                required_expertise=dna.required_expertise,
                potential_solution_areas=dna.potential_solution_areas,
                confidence_score=float(dna.confidence_score) if dna.confidence_score else None,
                signals=dna.signals,
                generated_by=dna.generated_by.value,
                analyzer_version=dna.analyzer_version,
                validation_status=dna.validation_status,
                validated_at=dna.validated_at,
                validated_by=dna.validated_by,
                created_at=dna.created_at,
                updated_at=dna.updated_at,
            )

        return AdminChallengeDetailResponse(
            id=challenge.id,
            title=challenge.title,
            description=challenge.description,
            location=challenge.location,
            status=challenge.status,
            created_at=challenge.created_at,
            updated_at=challenge.updated_at,
            image_path=challenge.image_path,
            latitude=challenge.latitude,
            longitude=challenge.longitude,
            dna=dna_detail,
        )

    def _get_challenge_with_dna(self, challenge_id: UUID) -> tuple[Challenge, ProblemDna | None]:
        """Get challenge with its DNA, raise if not found."""
        result = self.db.execute(
            select(Challenge, ProblemDna)
            .outerjoin(ProblemDna, ProblemDna.challenge_id == Challenge.id)
            .where(Challenge.id == challenge_id)
        ).first()
        if not result:
            raise NotFoundError("Challenge", challenge_id)
        return result

    # --- Status Transitions -----------------------------------------------

    def transition_challenge_status(
        self,
        challenge_id: UUID,
        request: ChallengeStatusTransitionRequest,
        reviewer_id: UUID,
    ) -> Challenge:
        """Transition challenge status with validation and audit."""
        challenge = self.challenge_repo.get_by_id(challenge_id)
        if not challenge:
            raise NotFoundError("Challenge", challenge_id)

        previous_status = challenge.status
        new_status = request.status

        # Validate transition
        allowed = VALID_STATUS_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Invalid status transition from {previous_status.value} to {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        # Update challenge
        challenge.status = new_status
        self.db.flush()

        # Create audit record
        audit = ChallengeReviewAudit(
            challenge_id=challenge_id,
            reviewer_id=reviewer_id,
            action="status_transition",
            previous_status=previous_status,
            new_status=new_status,
            note=request.note,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(challenge)

        return challenge

    # --- DNA Validation ---------------------------------------------------

    def validate_dna(
        self,
        challenge_id: UUID,
        request: DNAValidationRequest,
        reviewer_id: UUID,
    ) -> ProblemDna:
        """Validate or update Problem DNA with audit."""
        challenge, dna = self._get_challenge_with_dna(challenge_id)
        if not dna:
            raise NotFoundError("Problem DNA for challenge", challenge_id)

        previous_validation_status = dna.validation_status

        # Update DNA fields if provided
        if request.primary_domain is not None:
            dna.primary_domain = request.primary_domain
        if request.urgency is not None:
            dna.urgency = request.urgency
        
        # Update validation status
        dna.validation_status = request.validation_status
        dna.validated_at = datetime.now(timezone.utc)
        dna.validated_by = reviewer_id
        
        self.db.flush()

        # Create audit record
        audit = ChallengeReviewAudit(
            challenge_id=challenge_id,
            reviewer_id=reviewer_id,
            action="dna_validation",
            previous_dna_validation_status=previous_validation_status,
            new_dna_validation_status=request.validation_status,
            note=request.note,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(dna)

        return dna

    # --- Audit History ----------------------------------------------------

    def get_challenge_audit(self, challenge_id: UUID) -> list[ChallengeReviewAudit]:
        """Get audit history for a challenge."""
        return self.db.execute(
            select(ChallengeReviewAudit)
            .where(ChallengeReviewAudit.challenge_id == challenge_id)
            .order_by(ChallengeReviewAudit.created_at.desc())
        ).scalars().all()

    # --- Institution Review Queue (thin wrapper) --------------------------

    def list_institutions_for_review(
        self, query: AdminInstitutionListQuery
    ) -> AdminInstitutionListResponse:
        """List institutions for admin review."""
        rows, total = self.institution_repo.list_institutions_admin(
            verification_status=query.verification_status,
            institution_type=query.institution_type,
            skip=query.skip,
            limit=query.limit,
        )

        items = [AdminInstitutionListItem.model_validate(row) for row in rows]
        return AdminInstitutionListResponse(
            items=items, total=total, skip=query.skip, limit=query.limit
        )