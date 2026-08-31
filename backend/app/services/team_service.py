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
from app.repositories.user_repository import UserRepository


class TeamService:
    """Business logic for teams.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.

    Authorization is database-backed — institution membership and team
    membership are resolved from the database at request time.
    """

    _ALLOWED_CREATOR_ROLES = (
        InstitutionMembershipRole.INSTITUTION_ADMIN,
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
        self.user_repository = UserRepository(db)

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

    # --- Team invitations ---------------------------------------------------

    def invite_member(
        self,
        team_id: UUID,
        invitee_user_id: UUID,
        inviter_user_id: UUID,
    ) -> TeamMembership:
        """Invite a user to join a team.

        Authorization (the caller is the active team lead) is enforced by
        the require_team_lead dependency before this service is reached.
        The invitee must already hold an ACTIVE faculty or student
        institution membership at the team's institution — resolved from
        the database, never trusted from the client.
        """
        team = self.get_team(team_id)
        if self.user_repository.get_by_id(invitee_user_id) is None:
            raise NotFoundError("User", invitee_user_id)

        existing = self.membership_repository.get_membership(team_id, invitee_user_id)
        if existing is not None:
            if existing.status == TeamMembershipStatus.ACTIVE:
                raise ConflictError(
                    "This user is already an active member of the team."
                )
            raise ConflictError(
                "This user already has a pending invitation to this team."
            )

        eligible = self.institution_membership_repository.has_role(
            invitee_user_id,
            team.institution_id,
            ("faculty", "student"),
        )
        if not eligible:
            raise ForbiddenError(
                "Invitee must have an active faculty or student membership "
                "at the team's institution."
            )

        try:
            membership = self.membership_repository.create(
                {
                    "team_id": team_id,
                    "user_id": invitee_user_id,
                    "role": TeamRole.MEMBER,
                    "status": TeamMembershipStatus.INVITED,
                    "invited_by": inviter_user_id,
                    "joined_at": None,
                }
            )
            self._commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "This user already has a membership on this team."
            ) from None

        self.db.refresh(membership)
        return membership

    def _resolve_invitation_for_user(
        self, team_id: UUID, membership_id: UUID, user_id: UUID
    ) -> TeamMembership:
        """Resolve an invitation row that belongs to the caller.

        Returns 404 when the membership does not exist or does not belong
        to this team, 403 when it belongs to another user (IDOR), and 409
        when it is no longer pending.
        """
        membership = self.membership_repository.get_membership_by_id(membership_id)
        if membership is None or membership.team_id != team_id:
            raise NotFoundError("TeamMembership", membership_id)
        if membership.user_id != user_id:
            raise ForbiddenError("You can only act on your own invitation.")
        if membership.status != TeamMembershipStatus.INVITED:
            raise ConflictError("This invitation is no longer pending.")
        return membership

    def accept_invitation(
        self, team_id: UUID, membership_id: UUID, user_id: UUID
    ) -> TeamMembership:
        """Accept a pending team invitation.

        The invitee's active faculty/student institution membership at the
        team's institution is re-validated at accept time, not just at
        invitation creation. joined_at is set server-side.
        """
        membership = self._resolve_invitation_for_user(
            team_id, membership_id, user_id
        )
        team = self.get_team(team_id)
        eligible = self.institution_membership_repository.has_role(
            user_id,
            team.institution_id,
            ("faculty", "student"),
        )
        if not eligible:
            raise ForbiddenError(
                "You no longer hold an active faculty or student membership "
                "at the team's institution."
            )

        membership.status = TeamMembershipStatus.ACTIVE
        membership.joined_at = datetime.now(timezone.utc)
        self._commit()
        self.db.refresh(membership)
        return membership

    def decline_invitation(
        self, team_id: UUID, membership_id: UUID, user_id: UUID
    ) -> TeamMembership:
        """Decline a pending team invitation by removing the invitation row."""
        membership = self._resolve_invitation_for_user(
            team_id, membership_id, user_id
        )
        self.membership_repository.delete(membership)
        self._commit()
        return membership

    # --- Leaving teams -----------------------------------------------------

    def leave_team(self, team_id: UUID, user_id: UUID) -> TeamMembership:
        """Remove an active non-lead member from a team.

        The active lead cannot leave; leadership must be transferred first
        (409). Leaving deletes the membership row.
        """
        self.get_team(team_id)
        membership = self.membership_repository.get_active_membership(
            team_id, user_id
        )
        if membership is None:
            raise ForbiddenError("You are not an active member of this team.")
        if membership.role == TeamRole.LEAD:
            raise ConflictError(
                "The team lead cannot leave the team. Transfer leadership first."
            )
        self.membership_repository.delete(membership)
        self._commit()
        return membership

    # --- Leadership --------------------------------------------------------

    def transfer_leadership(
        self, team_id: UUID, current_lead_id: UUID, new_lead_id: UUID
    ) -> TeamMembership:
        """Atomically transfer the active lead role to another active member.

        The current lead is demoted to member before the target is promoted,
        so the partial unique index (exactly one active lead per team) is
        never violated at any point. Runs in a single transaction.
        """
        self.get_team(team_id)
        if new_lead_id == current_lead_id:
            raise ConflictError("The new lead must be a different team member.")

        target = self.membership_repository.get_active_membership(
            team_id, new_lead_id
        )
        if target is None:
            raise ConflictError("The new lead must be an active team member.")
        if target.role == TeamRole.LEAD:
            raise ConflictError("This user is already the team lead.")

        try:
            self.membership_repository.demote_active_lead(team_id)
            promoted = self.membership_repository.promote_active_member(
                team_id, new_lead_id
            )
            if not promoted:
                raise ConflictError(
                    "The target is no longer an active team member."
                )
            self._commit()
        except ConflictError:
            self.db.rollback()
            raise
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "Leadership transfer failed: the team must keep exactly one "
                "active lead."
            ) from None

        self.db.refresh(target)
        return target

    # --- Pending invitations ------------------------------------------------

    def list_my_invitations(self, user_id: UUID) -> list[TeamMembership]:
        """Return the user's pending team invitations (no team membership required)."""
        return self.membership_repository.list_invitations_for_user(user_id)

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise