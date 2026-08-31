from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.institution_membership import InstitutionMembership


class MembershipRepository:
    """Database access for institution memberships.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> InstitutionMembership:
        membership = InstitutionMembership(**data)
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_membership(
        self, user_id: UUID, institution_id: UUID
    ) -> InstitutionMembership | None:
        return self.db.execute(
            select(InstitutionMembership).where(
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.institution_id == institution_id,
            )
        ).scalar_one_or_none()

    def get_user_memberships(self, user_id: UUID) -> list[InstitutionMembership]:
        return list(
            self.db.execute(
                select(InstitutionMembership).where(
                    InstitutionMembership.user_id == user_id
                )
            ).scalars().all()
        )

    def has_role(
        self,
        user_id: UUID,
        institution_id: UUID,
        roles: tuple[str, ...],
    ) -> bool:
        return self.db.execute(
            select(func.count()).select_from(
                select(InstitutionMembership).where(
                    InstitutionMembership.user_id == user_id,
                    InstitutionMembership.institution_id == institution_id,
                    InstitutionMembership.role.in_(roles),
                    InstitutionMembership.status == "active",
                ).subquery()
            )
        ).scalar_one() > 0

    def count_active_institution_admins(self, institution_id: UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(
                select(InstitutionMembership).where(
                    InstitutionMembership.institution_id == institution_id,
                    InstitutionMembership.role == "institution_admin",
                    InstitutionMembership.status == "active",
                ).subquery()
            )
        ).scalar_one()
