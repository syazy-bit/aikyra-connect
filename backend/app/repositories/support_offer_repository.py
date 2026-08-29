from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.support_offer import SupportOffer


class SupportOfferRepository:
    """Database access for support offers.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> SupportOffer:
        offer = SupportOffer(**data)
        self.db.add(offer)
        self.db.flush()
        return offer

    def list_for_project(self, project_id: UUID) -> list[SupportOffer]:
        return list(
            self.db.execute(
                select(SupportOffer)
                .where(SupportOffer.project_id == project_id)
                .order_by(SupportOffer.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_organization(self, organization_id: UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)
