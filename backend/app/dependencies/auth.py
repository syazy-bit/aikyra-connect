"""Authentication/authorization dependencies for route protection.

Authorization is resolved from the institution_memberships database — never
from JWT claims, client-supplied role, or client-supplied user_id.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, NotAuthenticatedError
from app.models.user import User
from app.repositories.institution_repository import InstitutionRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.team_repository import TeamMembershipRepository, TeamRepository
from app.services.auth_service import AuthService


def _extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """Extract the Bearer token from the Authorization header."""
    if authorization is None:
        raise NotAuthenticatedError("Missing Authorization header.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise NotAuthenticatedError("Invalid Authorization header format.")
    token = parts[1].strip()
    if not token:
        raise NotAuthenticatedError("Missing Bearer token.")
    return token


def get_current_user(
    token: Annotated[str, Depends(_extract_bearer_token)],
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer token.

    Raises NotAuthenticatedError for missing, invalid, or expired tokens.
    """
    service = AuthService(db)
    return service.resolve_current_user(token)


def require_owner_or_rep(
    institution_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorization dependency: requires an ACTIVE owner or representative
    membership for the given institution.

    Resolves membership from the database — never trusts JWT claims or
    client-supplied role.

    Raises NotFoundError if the institution does not exist.
    Raises ForbiddenError if the user lacks the required membership.
    """
    institution_repo = InstitutionRepository(db)
    if institution_repo.get_by_id(institution_id) is None:
        raise NotFoundError("Institution", institution_id)
    membership_repo = MembershipRepository(db)
    has_access = membership_repo.has_role(
        current_user.id,
        institution_id,
        ("owner", "representative"),
    )
    if not has_access:
        raise ForbiddenError(
            "You do not have permission to modify this institution."
        )
    return current_user


def require_reviewer(
    institution_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorization dependency: requires an ACTIVE reviewer membership
    for the given institution.

    Resolves membership from the database — never trusts JWT claims or
    client-supplied role.

    Raises NotFoundError if the institution does not exist.
    Raises ForbiddenError if the user lacks the required membership.
    """
    institution_repo = InstitutionRepository(db)
    if institution_repo.get_by_id(institution_id) is None:
        raise NotFoundError("Institution", institution_id)
    membership_repo = MembershipRepository(db)
    has_access = membership_repo.has_role(
        current_user.id,
        institution_id,
        ("reviewer",),
    )
    if not has_access:
        raise ForbiddenError(
            "You do not have reviewer permissions for this institution."
        )
    return current_user


def require_team_member(
    team_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorization dependency: requires an ACTIVE team membership.

    Resolves membership from the database — never trusts JWT claims or
    client-supplied role.

    Raises NotFoundError if the team does not exist.
    Raises ForbiddenError if the user lacks an active membership on the team.
    """
    team_repo = TeamRepository(db)
    if team_repo.get_by_id(team_id) is None:
        raise NotFoundError("Team", team_id)
    membership_repo = TeamMembershipRepository(db)
    membership = membership_repo.get_active_membership(team_id, current_user.id)
    if membership is None:
        raise ForbiddenError(
            "You are not an active member of this team."
        )
    return current_user


def require_team_lead(
    team_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorization dependency: requires ACTIVE team lead membership.

    Resolves membership from the database — never trusts JWT claims or
    client-supplied role.

    Raises NotFoundError if the team does not exist.
    Raises ForbiddenError if the user is not the active lead of the team.
    """
    team_repo = TeamRepository(db)
    if team_repo.get_by_id(team_id) is None:
        raise NotFoundError("Team", team_id)
    membership_repo = TeamMembershipRepository(db)
    membership = membership_repo.get_lead_membership(team_id)
    if membership is None or membership.user_id != current_user.id:
        raise ForbiddenError(
            "You must be the team lead to perform this action."
        )
    return current_user
