from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization


def normalized_name_expr():
    """Normalized-name expression — mirrors the `uq_organizations_name_normalized`
    index expression so the service-level duplicate pre-check matches the DB
    constraint exactly."""
    cleaned = func.regexp_replace(
        func.regexp_replace(Organization.name, "[^a-zA-Z0-9]+", " ", "g"),
        r"\s+",
        " ",
        "g",
    )
    return func.lower(func.btrim(cleaned))


class OrganizationRepository:
    """Database access for organizations.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Organization:
        organization = Organization(**data)
        self.db.add(organization)
        self.db.flush()
        return organization

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_exact_normalized_name(self, normalized_name: str) -> Organization | None:
        return self.db.execute(
            select(Organization).where(normalized_name_expr() == normalized_name)
        ).scalar_one_or_none()

    def get_by_manager(self, manager_user_id: UUID) -> Organization | None:
        return self.db.execute(
            select(Organization).where(
                Organization.manager_user_id == manager_user_id
            )
        ).scalar_one_or_none()
