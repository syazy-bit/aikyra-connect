from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.challenge import Challenge
from app.models.institution import Institution
from app.models.institution_membership import (
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.team import Team, TeamMembership, TeamMembershipStatus, TeamRole, TeamStatus
from app.repositories.institution_repository import InstitutionRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.team_repository import TeamMembershipRepository, TeamRepository


class TeamService:
    """Business logic for teams.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.

    Authorization is database-backed — institution membership and team
    membership are resolved from the database at request time.
    """

    _ALLOWED_CREATOR_ROLES = (
        InstitutionMembershipRole.OWNER,
        InstitutionMembershipRole.REPRESENTATIVE,
        InstitutionMembershipRole.FACULTY,
        InstitutionMembershipRole.STUDENT,
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TeamRepository(db)
        self.membership_repository = TeamMembershipRepository(db)
        self.institution_repository = InstitutionRepository(db)
        self.institution_membership_repository = MembershipRepository(db)

    # --- Team creation ------------------------------------------------------

    def create_team(
        self,
        institution_id: UUID,
        challenge_id: UUID,
        name: str,
        description: str | None,
        creator_user_id: UUID,
    ) -> Team:
        # Validate institution exists
        institution = self.institution_repository.get_by_id(institution_id)
        if institution is None:
            raise NotFoundError("Institution", institution_id)

        # Validate challenge exists
        challenge = self.db.get(Challenge, challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge", challenge_id)

        # Validate creator has active membership at the institution
        creator_membership = self.institution_membership_repository.get_membership(
            creator_user_id, institution_id
        )
        if creator_membership is None:
            raise ForbiddenError(
                "You do not have an active membership at this institution."
            )
        if creator_membership.status != InstitutionMembershipStatus.ACTIVE:
            raise ForbiddenError(
                "Your institution membership is not active."
            )
        if creator_membership.role not in self._ALLOWED_CREATOR_ROLES:
            raise ForbiddenError(
                "Your institution role does not permit team creation."
            )

        # Check for duplicate team name within same institution + challenge
        existing = self.repository.get_by_institution_challenge_name(
            institution_id, challenge_id, name
        )
        if existing is not None:
            raise ConflictError(
                f"A team with this name already exists for this challenge at this institution "
                f"(id: {existing.id})."
            )

        try:
            # Create the team
            team = self.repository.create(
                {
                    "institution_id": institution_id,
                    "challenge_id": challenge_id,
                    "name": name,
                    "description": description,
                    "status": TeamStatus.FORMING,
                    "created_by": creator_user_id,
                }
            )

            # Create the creator's team membership as lead
            self.membership_repository.create(
                {
                    "team_id": team.id,
                    "user_id": creator_user_id,
                    "role": TeamRole.LEAD,
                    "status": TeamMembershipStatus.ACTIVE,
                    "invited_by": None,
                    "joined_at": datetime.now(timezone.utc),
                }
            )

            self._commit()
        except ConflictError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "A team with this name already exists for this challenge at this institution."
            ) from None

        self.db.refresh(team)
        return team

    # --- Team retrieval -----------------------------------------------------

    def get_team(self, team_id: UUID) -> Team:
        team = self.repository.get_by_id(team_id)
        if team is None:
            raise NotFoundError("Team", team_id)
        return team

    def list_visible_teams(
        self,
        user_id: UUID,
        institution_id: UUID | None = None,
        challenge_id: UUID | None = None,
        status: TeamStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Team], int]:
        """List teams the user is authorized to see.

        Authorization is database-backed. A user only discovers teams from
        institutions where they hold an active membership, or teams they
        belong to.
        """
        return self.repository.list_visible_teams(
            user_id=user_id,
            institution_id=institution_id,
            challenge_id=challenge_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    # --- Team update --------------------------------------------------------

    def update_team(
        self, team_id: UUID, name: str | None, description: str | None
    ) -> Team:
        team = self.get_team(team_id)

        data: dict = {}
        if name is not None:
            # Check for duplicate name within same institution + challenge
            existing = self.repository.get_by_institution_challenge_name(
                team.institution_id, team.challenge_id, name
            )
            if existing is not None and existing.id != team.id:
                raise ConflictError(
                    f"A team with this name already exists for this challenge at this institution "
                    f"(id: {existing.id})."
                )
            data["name"] = name
        if description is not None:
            data["description"] = description

        if not data:
            return team

        try:
            updated = self.repository.update(team, data)
            self._commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "A team with this name already exists for this challenge at this institution."
            ) from None

        self.db.refresh(updated)
        return updated

    # --- Team membership ----------------------------------------------------

    def list_members(
        self, team_id: UUID, status: TeamMembershipStatus | None = None
    ) -> list[TeamMembership]:
        return self.membership_repository.get_memberships_for_team(team_id, status)

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise