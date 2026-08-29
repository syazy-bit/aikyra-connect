from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.organization import Organization
from app.models.project import Project, ProjectStatus
from app.models.support_offer import SupportOffer, SupportOfferStatus, SupportType
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.support_offer_repository import SupportOfferRepository


def _normalize_name(name: str) -> str:
    import re

    without_punctuation = re.sub(r"[^a-zA-Z0-9]+", " ", name.lower())
    return re.sub(r"\s+", " ", without_punctuation).strip()


class ProjectService:
    """Business logic for approved projects, organizations and support offers.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.

    Authorization is database-backed. An offer's organization is derived
    from the authenticated user's manager relationship — never from the
    client — so users cannot pose as an organization they do not manage.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.organization_repository = OrganizationRepository(db)
        self.offer_repository = SupportOfferRepository(db)

    # --- Projects ----------------------------------------------------------

    def list_projects(
        self,
        status: ProjectStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        projects, total = self.project_repository.list_projects(
            status=status, skip=skip, limit=limit
        )
        return [self._to_list_item(p) for p in projects], total

    def _to_list_item(self, project: Project) -> dict:
        institution = self.project_repository.get_institution(project.institution_id)
        team = self.project_repository.get_team(project.team_id)
        challenge = self.project_repository.get_challenge(project.challenge_id)
        offers = self.offer_repository.list_for_project(project.id)
        return {
            "id": project.id,
            "title": project.title,
            "team_id": project.team_id,
            "status": project.status,
            "institution_name": institution.name if institution else "—",
            "team_name": team.name if team else "—",
            "challenge_title": challenge.title if challenge else "—",
            "offer_count": len(offers),
            "created_at": project.created_at,
        }

    def get_project(self, project_id: UUID) -> dict | None:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            return None
        institution = self.project_repository.get_institution(project.institution_id)
        team = self.project_repository.get_team(project.team_id)
        challenge = self.project_repository.get_challenge(project.challenge_id)
        offers = self.offer_repository.list_for_project(project.id)
        offer_refs = []
        for offer in offers:
            org = self.offer_repository.get_organization(offer.organization_id)
            offer_refs.append(
                {
                    "id": offer.id,
                    "organization": {
                        "id": offer.organization_id,
                        "name": org.name if org else "—",
                    },
                    "support_type": offer.support_type,
                    "message": offer.message,
                    "status": offer.status,
                    "created_at": offer.created_at,
                }
            )
        return {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "institution_name": institution.name if institution else "—",
            "team_name": team.name if team else "—",
            "challenge_title": challenge.title if challenge else "—",
            "offers": offer_refs,
            "created_at": project.created_at,
        }

    # --- Organizations -----------------------------------------------------

    def create_organization(
        self,
        name: str,
        manager_user_id: UUID,
        description: str | None = None,
        website: str | None = None,
    ) -> Organization:
        normalized = _normalize_name(name)
        if self.organization_repository.get_by_exact_normalized_name(normalized):
            raise ConflictError("An organization with this name already exists.")
        if self.organization_repository.get_by_manager(manager_user_id):
            raise ConflictError("You already manage an organization.")

        try:
            organization = self.organization_repository.create(
                {
                    "name": name,
                    "description": description,
                    "website": website,
                    "manager_user_id": manager_user_id,
                }
            )
            self._commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("An organization with this name already exists.") from None
        self.db.refresh(organization)
        return organization

    def get_organization_by_manager(self, manager_user_id: UUID) -> Organization | None:
        return self.organization_repository.get_by_manager(manager_user_id)

    # --- Support offers ----------------------------------------------------

    def create_offer(
        self,
        project_id: UUID,
        support_type: SupportType,
        user_id: UUID,
        message: str | None = None,
    ) -> SupportOffer:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        if project.status != ProjectStatus.ACTIVE:
            raise ConflictError("This project is not open to support offers.")

        organization = self.organization_repository.get_by_manager(user_id)
        if organization is None:
            raise ForbiddenError(
                "Register an organization before offering support."
            )

        try:
            offer = self.offer_repository.create(
                {
                    "project_id": project.id,
                    "organization_id": organization.id,
                    "offered_by": user_id,
                    "support_type": support_type,
                    "message": message,
                    "status": SupportOfferStatus.OFFERED,
                }
            )
            self._commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("This support offer could not be saved.") from None
        self.db.refresh(offer)
        return offer

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
