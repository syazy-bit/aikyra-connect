from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.proposal import Proposal, ProposalStatus
from app.models.team import Team, TeamRole
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.proposal_repository import ProposalRepository
from app.repositories.team_repository import TeamMembershipRepository, TeamRepository


class ProposalService:
    """Business logic for solution proposals (CP3 core + CP4 review).

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.

    Authorization is database-backed — team membership and institution
    membership (owner/representative) are resolved from the database at
    request time. Client-supplied role, status, ownership and membership
    data is never trusted.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProposalRepository(db)
        self.team_repository = TeamRepository(db)
        self.team_membership_repository = TeamMembershipRepository(db)
        self.institution_membership_repository = MembershipRepository(db)
        self.challenge_repository = ChallengeRepository(db)

    # --- Authorization helpers (DB-backed) ----------------------------------

    def _get_active_membership(self, team_id: UUID, user_id: UUID):
        return self.team_membership_repository.get_active_membership(team_id, user_id)

    def _is_lead(self, team_id: UUID, user_id: UUID) -> bool:
        membership = self._get_active_membership(team_id, user_id)
        return membership is not None and membership.role == TeamRole.LEAD

    def _can_view(self, team: Team, user_id: UUID) -> bool:
        """Viewing is limited to active team members or active institution
        owners/representatives of the team's institution."""
        if self._get_active_membership(team.id, user_id) is not None:
            return True
        return self.institution_membership_repository.has_role(
            user_id, team.institution_id, ("owner", "representative")
        )

    def _can_review(self, team: Team, reviewer_user_id: UUID) -> bool:
        """A reviewer must be an ACTIVE owner or representative of the
        institution the proposal's team belongs to. Platform reviewers,
        students and ordinary team members never qualify."""
        return self.institution_membership_repository.has_role(
            reviewer_user_id, team.institution_id, ("owner", "representative")
        )

    def _require_reviewer(
        self, proposal: Proposal, reviewer_user_id: UUID
    ) -> None:
        """Ensure the user may review this proposal, raising 403 otherwise.

        The proposeal's institution is resolved from the database via its
        team — never from client input."""
        team = self.team_repository.get_by_id(proposal.team_id)
        if team is None:
            raise NotFoundError("Team", proposal.team_id)
        if not self._can_review(team, reviewer_user_id):
            raise ForbiddenError(
                "You do not have permission to review this proposal."
            )

    def _require_visible_proposal(self, proposal_id: UUID, user_id: UUID) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)
        team = self.team_repository.get_by_id(proposal.team_id)
        if team is None or not self._can_view(team, user_id):
            raise ForbiddenError("You do not have access to this proposal.")
        return proposal

    # --- Create --------------------------------------------------------------

    def create_proposal(
        self,
        team_id: UUID,
        challenge_id: UUID,
        title: str,
        summary: str,
        approach: str | None,
        resources_needed: str | None,
        timeline: str | None,
        creator_user_id: UUID,
    ) -> Proposal:
        team = self.team_repository.get_by_id(team_id)
        if team is None:
            raise NotFoundError("Team", team_id)

        challenge = self.challenge_repository.get_by_id(challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge", challenge_id)

        if team.challenge_id != challenge_id:
            raise ConflictError(
                "challenge_id does not match the challenge this team is working on."
            )

        if self._get_active_membership(team_id, creator_user_id) is None:
            raise ForbiddenError("You are not an active member of this team.")

        existing = self.repository.get_by_team_challenge(team_id, challenge_id)
        if existing is not None:
            raise ConflictError(
                "This team already has a proposal for this challenge."
            )

        try:
            proposal = self.repository.create(
                {
                    "team_id": team_id,
                    "challenge_id": challenge_id,
                    "title": title,
                    "summary": summary,
                    "approach": approach,
                    "resources_needed": resources_needed,
                    "timeline": timeline,
                    "status": ProposalStatus.DRAFT,
                }
            )
            self._commit()
        except ConflictError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "This team already has a proposal for this challenge."
            ) from None

        self.db.refresh(proposal)
        return proposal

    # --- Retrieval ------------------------------------------------------------

    def list_proposals(
        self,
        user_id: UUID,
        team_id: UUID | None = None,
        status: ProposalStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Proposal], int]:
        return self.repository.list_visible(
            user_id=user_id,
            team_id=team_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def get_proposal(self, proposal_id: UUID, user_id: UUID) -> Proposal:
        return self._require_visible_proposal(proposal_id, user_id)

    # --- Edit (draft only) --------------------------------------------------

    def update_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
        fields: dict,
    ) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        if self._get_active_membership(proposal.team_id, user_id) is None:
            raise ForbiddenError("You are not an active member of this team.")

        if proposal.status != ProposalStatus.DRAFT:
            raise ConflictError("Only draft proposals can be edited.")

        if not fields:
            return proposal

        try:
            updated = self.repository.update(proposal, fields)
            self._commit()
        except ConflictError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("This proposal could not be updated.") from None

        self.db.refresh(updated)
        return updated

    # --- Submit (draft -> submitted, lead only) ------------------------------

    def submit_proposal(self, proposal_id: UUID, lead_user_id: UUID) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        if not self._is_lead(proposal.team_id, lead_user_id):
            raise ForbiddenError("Only the active team lead can submit a proposal.")

        if proposal.status != ProposalStatus.DRAFT:
            raise ConflictError("Only draft proposals can be submitted.")

        proposal.status = ProposalStatus.SUBMITTED
        proposal.submitted_at = datetime.now(timezone.utc)
        self._commit()
        self.db.refresh(proposal)
        return proposal

    # --- Withdraw (draft|submitted -> withdrawn, lead only) ------------------

    def withdraw_proposal(self, proposal_id: UUID, lead_user_id: UUID) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        if not self._is_lead(proposal.team_id, lead_user_id):
            raise ForbiddenError("Only the active team lead can withdraw a proposal.")

        if proposal.status == ProposalStatus.WITHDRAWN:
            raise ConflictError("This proposal has already been withdrawn.")

        if proposal.status not in (
            ProposalStatus.DRAFT,
            ProposalStatus.SUBMITTED,
        ):
            raise ConflictError("Only draft or submitted proposals can be withdrawn.")

        proposal.status = ProposalStatus.WITHDRAWN
        self._commit()
        self.db.refresh(proposal)
        return proposal

    # --- Review: submitted -> under_review -> accepted|rejected (CP4) --------
    # The review workflow is institution-owned: only an ACTIVE owner or
    # representative of the proposal's team institution may advance the state
    # machine. rejected/accepted are terminal — there is no resubmission,
    # appeal or second-round review. reviewed_at and reviewed_by are set
    # server-side from the authenticated reviewer at the final decision.

    def start_review(
        self, proposal_id: UUID, reviewer_user_id: UUID
    ) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        self._require_reviewer(proposal, reviewer_user_id)

        if proposal.status != ProposalStatus.SUBMITTED:
            raise ConflictError(
                "Only submitted proposals can be moved into review."
            )

        proposal.status = ProposalStatus.UNDER_REVIEW
        self._commit()
        self.db.refresh(proposal)
        return proposal

    def accept_proposal(
        self,
        proposal_id: UUID,
        reviewer_user_id: UUID,
        review_note: str | None = None,
    ) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        self._require_reviewer(proposal, reviewer_user_id)

        if proposal.status != ProposalStatus.UNDER_REVIEW:
            raise ConflictError(
                "Only proposals under review can be accepted."
            )

        proposal.status = ProposalStatus.ACCEPTED
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.reviewed_by = reviewer_user_id
        proposal.review_note = review_note
        self._commit()
        self.db.refresh(proposal)
        return proposal

    def reject_proposal(
        self,
        proposal_id: UUID,
        reviewer_user_id: UUID,
        review_note: str | None = None,
    ) -> Proposal:
        proposal = self.repository.get_by_id(proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)

        self._require_reviewer(proposal, reviewer_user_id)

        if proposal.status != ProposalStatus.UNDER_REVIEW:
            raise ConflictError(
                "Only proposals under review can be rejected."
            )

        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_at = datetime.now(timezone.utc)
        proposal.reviewed_by = reviewer_user_id
        proposal.review_note = review_note
        self._commit()
        self.db.refresh(proposal)
        return proposal

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise