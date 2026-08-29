from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge
from app.models.institution import Institution
from app.models.project import Project, ProjectStatus
from app.models.team import Team


class ProjectRepository:
    """Database access for projects (approved solutions).

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Project:
        project = Project(**data)
        self.db.add(project)
        self.db.flush()
        return project

    def get_by_id(self, project_id: UUID) -> Project | None:
        return self.db.get(Project, project_id)

    def get_by_proposal(self, proposal_id: UUID) -> Project | None:
        return self.db.execute(
            select(Project).where(Project.proposal_id == proposal_id)
        ).scalar_one_or_none()

    def list_projects(
        self,
        status: ProjectStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Project], int]:
        """Public listing of approved projects.

        Projects exist only for accepted proposals, so this surface is
        inherently limited to approved solutions.
        """
        query = select(Project)
        count_query = select(func.count()).select_from(Project)
        if status is not None:
            query = query.where(Project.status == status)
            count_query = count_query.where(Project.status == status)
        total = self.db.execute(count_query).scalar_one()
        rows = (
            self.db.execute(
                query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def get_institution(self, institution_id: UUID) -> Institution | None:
        return self.db.get(Institution, institution_id)

    def get_team(self, team_id: UUID) -> Team | None:
        return self.db.get(Team, team_id)

    def get_challenge(self, challenge_id: UUID) -> Challenge | None:
        return self.db.get(Challenge, challenge_id)
