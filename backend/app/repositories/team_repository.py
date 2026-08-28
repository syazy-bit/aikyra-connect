from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipStatus,
)
from app.models.team import Team, TeamMembership, TeamMembershipStatus, TeamRole, TeamStatus


class TeamRepository:
    """Database access for teams.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Team:
        team = Team(**data)
        self.db.add(team)
        self.db.flush()
        return team

    def get_by_id(self, team_id: UUID) -> Team | None:
        return self.db.execute(
            select(Team).where(Team.id == team_id)
        ).scalar_one_or_none()

    def get_by_institution_challenge_name(
        self, institution_id: UUID, challenge_id: UUID, name: str
    ) -> Team | None:
        return self.db.execute(
            select(Team).where(
                Team.institution_id == institution_id,
                Team.challenge_id == challenge_id,
                Team.name == name,
            )
        ).scalar_one_or_none()

    def list_teams(
        self,
        institution_id: UUID | None = None,
        challenge_id: UUID | None = None,
        status: TeamStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Team], int]:
        query = select(Team)
        count_query = select(func.count()).select_from(Team)

        if institution_id is not None:
            query = query.where(Team.institution_id == institution_id)
            count_query = count_query.where(Team.institution_id == institution_id)
        if challenge_id is not None:
            query = query.where(Team.challenge_id == challenge_id)
            count_query = count_query.where(Team.challenge_id == challenge_id)
        if status is not None:
            query = query.where(Team.status == status)
            count_query = count_query.where(Team.status == status)

        query = query.order_by(Team.created_at.desc()).offset(skip).limit(limit)
        teams = list(self.db.execute(query).scalars().all())
        total = self.db.execute(count_query).scalar_one()
        return teams, total

    def list_visible_teams(
        self,
        user_id: UUID,
        institution_id: UUID | None = None,
        challenge_id: UUID | None = None,
        status: TeamStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Team], int]:
        """List teams the authenticated user is allowed to see.

        A team is visible to a user only if they have an ACTIVE institution
        membership at the team's institution, or an ACTIVE team membership.
        Membership is resolved from the database — never trusted from the
        client.
        """
        active_institutions = (
            select(InstitutionMembership.institution_id).where(
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.status == InstitutionMembershipStatus.ACTIVE,
            )
        )
        active_teams = (
            select(TeamMembership.team_id).where(
                TeamMembership.user_id == user_id,
                TeamMembership.status == TeamMembershipStatus.ACTIVE,
            )
        )
        visible = or_(
            Team.institution_id.in_(active_institutions),
            Team.id.in_(active_teams),
        )

        query = select(Team).where(visible)
        count_query = select(func.count()).select_from(Team).where(visible)

        if institution_id is not None:
            query = query.where(Team.institution_id == institution_id)
            count_query = count_query.where(Team.institution_id == institution_id)
        if challenge_id is not None:
            query = query.where(Team.challenge_id == challenge_id)
            count_query = count_query.where(Team.challenge_id == challenge_id)
        if status is not None:
            query = query.where(Team.status == status)
            count_query = count_query.where(Team.status == status)

        query = query.order_by(Team.created_at.desc()).offset(skip).limit(limit)
        teams = list(self.db.execute(query).scalars().all())
        total = self.db.execute(count_query).scalar_one()
        return teams, total

    def update(self, team: Team, data: dict) -> Team:
        for key, value in data.items():
            setattr(team, key, value)
        self.db.flush()
        return team


class TeamMembershipRepository:
    """Database access for team memberships.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> TeamMembership:
        membership = TeamMembership(**data)
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_membership(
        self, team_id: UUID, user_id: UUID
    ) -> TeamMembership | None:
        return self.db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        ).scalar_one_or_none()

    def get_active_membership(
        self, team_id: UUID, user_id: UUID
    ) -> TeamMembership | None:
        return self.db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
                TeamMembership.status == TeamMembershipStatus.ACTIVE,
            )
        ).scalar_one_or_none()

    def get_memberships_for_team(
        self, team_id: UUID, status: TeamMembershipStatus | None = None
    ) -> list[TeamMembership]:
        query = select(TeamMembership).where(TeamMembership.team_id == team_id)
        if status is not None:
            query = query.where(TeamMembership.status == status)
        return list(self.db.execute(query).scalars().all())

    def get_lead_membership(self, team_id: UUID) -> TeamMembership | None:
        return self.db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.role == TeamRole.LEAD,
                TeamMembership.status == TeamMembershipStatus.ACTIVE,
            )
        ).scalar_one_or_none()

    def has_active_lead(self, team_id: UUID) -> bool:
        return self.db.execute(
            select(func.count()).select_from(
                select(TeamMembership).where(
                    TeamMembership.team_id == team_id,
                    TeamMembership.role == TeamRole.LEAD,
                    TeamMembership.status == TeamMembershipStatus.ACTIVE,
                ).subquery()
            )
        ).scalar_one() > 0

    def count_active_members(self, team_id: UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(
                select(TeamMembership).where(
                    TeamMembership.team_id == team_id,
                    TeamMembership.status == TeamMembershipStatus.ACTIVE,
                ).subquery()
            )
        ).scalar_one()

    def update(self, membership: TeamMembership, data: dict) -> TeamMembership:
        for key, value in data.items():
            setattr(membership, key, value)
        self.db.flush()
        return membership