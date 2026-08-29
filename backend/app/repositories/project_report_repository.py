from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_report import ProjectReport


class ProjectReportRepository:
    """Database access for project outcome reports (CP8).

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.

    A report is a project singleton (1:1, unique project_id): every lookup is
    by project_id, so a report can never be reached through another project's
    URL — cross-project access is structurally impossible.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_project(self, project_id: UUID) -> ProjectReport | None:
        return self.db.execute(
            select(ProjectReport).where(ProjectReport.project_id == project_id)
        ).scalar_one_or_none()

    def create(self, data: dict) -> ProjectReport:
        report = ProjectReport(**data)
        self.db.add(report)
        self.db.flush()
        return report

    def update(self, report: ProjectReport, data: dict) -> ProjectReport:
        for key, value in data.items():
            setattr(report, key, value)
        self.db.flush()
        return report

    def delete(self, report: ProjectReport) -> None:
        self.db.delete(report)
        self.db.flush()