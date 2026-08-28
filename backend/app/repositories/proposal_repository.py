from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipStatus,
)
from app.models.proposal import Proposal, ProposalStatus
from app.models.team import Team, TeamMembership, TeamMembershipStatus


_VIEW_INSTITUTION_ROLES = ("owner", "representative")


class ProposalRepository:
    """Database access for proposals.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Proposal:
        proposal = Proposal(**data)
        self.db.add(proposal)
        self.db.flush()
        return proposal

    def get_by_id(self, proposal_id: UUID) -> Proposal | None:
        return self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        ).scalar_one_or_none()

    def get_by_team_challenge(
        self, team_id: UUID, challenge_id: UUID
    ) -> Proposal | None:
        return self.db.execute(
            select(Proposal).where(
                Proposal.team_id == team_id,
                Proposal.challenge_id == challenge_id,
            )
        ).scalar_one_or_none()

    def update(self, proposal: Proposal, data: dict) -> Proposal:
        for key, value in data.items():
            setattr(proposal, key, value)
        self.db.flush()
        return proposal

    def list_visible(
        self,
        user_id: UUID,
        team_id: UUID | None = None,
        status: ProposalStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Proposal], int]:
        """List proposals the authenticated user is allowed to see.

        A proposal is visible only if the user holds an ACTIVE membership on
        its team, or an ACTIVE owner/representative institution membership at
        the team's institution. Membership is resolved from the database —
        never trusted from the client. This is deliberately stricter than team
        discovery: students/faculty at the institution cannot view proposals.
        """
        visible = self._visibility_predicate(user_id)

        query = select(Proposal).where(visible)
        count_query = select(func.count()).select_from(Proposal).where(visible)

        if team_id is not None:
            query = query.where(Proposal.team_id == team_id)
            count_query = count_query.where(Proposal.team_id == team_id)
        if status is not None:
            query = query.where(Proposal.status == status)
            count_query = count_query.where(Proposal.status == status)

        query = query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit)
        proposals = list(self.db.execute(query).scalars().all())
        total = self.db.execute(count_query).scalar_one()
        return proposals, total

    @staticmethod
    def _visibility_predicate(user_id: UUID):
        active_teams = (
            select(TeamMembership.team_id).where(
                TeamMembership.user_id == user_id,
                TeamMembership.status == TeamMembershipStatus.ACTIVE,
            )
        )
        owning_institutions = (
            select(InstitutionMembership.institution_id).where(
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.status == InstitutionMembershipStatus.ACTIVE,
                InstitutionMembership.role.in_(_VIEW_INSTITUTION_ROLES),
            )
        )
        owning_teams = (
            select(Team.id).where(Team.institution_id.in_(owning_institutions))
        )
        return or_(
            Proposal.team_id.in_(active_teams),
            Proposal.team_id.in_(owning_teams),
        )