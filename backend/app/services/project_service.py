from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.organization import Organization
from app.models.project import Project, ProjectStatus
from app.models.project_impact_metric import ProjectImpactMetric
from app.models.support_offer import SupportOffer, SupportOfferStatus, SupportType
from app.models.team import TeamRole
from app.repositories.impact_metric_repository import ImpactMetricRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.support_offer_repository import SupportOfferRepository
from app.repositories.team_repository import TeamMembershipRepository


def _normalize_name(name: str) -> str:
    import re

    without_punctuation = re.sub(r"[^a-zA-Z0-9]+", " ", name.lower())
    return re.sub(r"\s+", " ", without_punctuation).strip()


# CP6 lifecycle: the only legal forward transitions. Everything else —
# including staying put and any backwards jump — is a 409 conflict.
PROJECT_LIFECYCLE_TRANSITIONS = {
    ProjectStatus.PROTOTYPE: frozenset({ProjectStatus.PILOT}),
    ProjectStatus.PILOT: frozenset({ProjectStatus.IMPLEMENTED}),
    ProjectStatus.IMPLEMENTED: frozenset(),
}


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
        self.team_membership_repository = TeamMembershipRepository(db)
        self.impact_metric_repository = ImpactMetricRepository(db)

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
        impact_metrics = self.impact_metric_repository.list_for_project(project.id)
        return {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "team_id": project.team_id,
            "institution_name": institution.name if institution else "—",
            "team_name": team.name if team else "—",
            "challenge_title": challenge.title if challenge else "—",
            "offers": offer_refs,
            "impact": [
                {
                    "id": metric.id,
                    "project_id": metric.project_id,
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "description": metric.description,
                    "created_at": metric.created_at,
                    "updated_at": metric.updated_at,
                }
                for metric in impact_metrics
            ],
            "created_at": project.created_at,
        }

    # --- Lifecycle (CP6) ---------------------------------------------------

    def transition_lifecycle(
        self, project_id: UUID, new_status: ProjectStatus, user_id: UUID
    ) -> dict:
        """Advance the project lifecycle as the team lead.

        Authorization is resolved entirely from the database at request
        time: the project -> its team -> the caller's ACTIVE team membership
        -> its LEAD role. Client-supplied identity, role and membership
        fields are never trusted.
        """
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)

        membership = self.team_membership_repository.get_active_membership(
            project.team_id, user_id
        )
        if membership is None or membership.role != TeamRole.LEAD:
            raise ForbiddenError(
                "Only the active team lead can advance the project lifecycle."
            )

        allowed = PROJECT_LIFECYCLE_TRANSITIONS.get(project.status, frozenset())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot transition project from '{project.status.value}' "
                f"to '{new_status.value}'."
            )

        project.status = new_status
        self._commit()
        self.db.refresh(project)
        return self.get_project(project.id)

    # --- Impact metrics (CP7) ----------------------------------------------

    def _require_project_lead(self, project_id: UUID, user_id: UUID) -> Project:
        """Resolve a project and verify the caller is its ACTIVE team lead.

        Authorization is resolved entirely from the database at request time:
        the project -> its team -> the caller's ACTIVE team membership -> its
        LEAD role. Client-supplied identity, role and membership fields are
        never trusted.

        Raises NotFoundError if the project does not exist.
        Raises ForbiddenError if the caller is not the active team lead.
        """
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)

        membership = self.team_membership_repository.get_active_membership(
            project.team_id, user_id
        )
        if membership is None or membership.role != TeamRole.LEAD:
            raise ForbiddenError(
                "Only the active team lead can manage impact metrics."
            )
        return project

    def list_impact_metrics(self, project_id: UUID) -> list[ProjectImpactMetric]:
        """Public listing of a project's impact metrics (newest-last)."""
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        return self.impact_metric_repository.list_for_project(project.id)

    def create_impact_metric(
        self,
        project_id: UUID,
        user_id: UUID,
        name: str,
        value: str,
        unit: str | None = None,
        description: str | None = None,
    ) -> ProjectImpactMetric:
        self._require_project_lead(project_id, user_id)
        try:
            metric = self.impact_metric_repository.create(
                {
                    "project_id": project_id,
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "description": description,
                }
            )
            self._commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("This impact metric could not be saved.") from None
        self.db.refresh(metric)
        return metric

    def update_impact_metric(
        self,
        project_id: UUID,
        metric_id: UUID,
        user_id: UUID,
        name: str,
        value: str,
        unit: str | None = None,
        description: str | None = None,
    ) -> ProjectImpactMetric:
        self._require_project_lead(project_id, user_id)
        metric = self.impact_metric_repository.get_in_project(metric_id, project_id)
        if metric is None:
            raise NotFoundError("ImpactMetric", metric_id)
        self.impact_metric_repository.update(
            metric,
            {
                "name": name,
                "value": value,
                "unit": unit,
                "description": description,
            },
        )
        self._commit()
        self.db.refresh(metric)
        return metric

    def delete_impact_metric(
        self, project_id: UUID, metric_id: UUID, user_id: UUID
    ) -> None:
        self._require_project_lead(project_id, user_id)
        metric = self.impact_metric_repository.get_in_project(metric_id, project_id)
        if metric is None:
            raise NotFoundError("ImpactMetric", metric_id)
        self.impact_metric_repository.delete(metric)
        self._commit()

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
        if project.status == ProjectStatus.IMPLEMENTED:
            raise ConflictError("This project is no longer open to support offers.")

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
