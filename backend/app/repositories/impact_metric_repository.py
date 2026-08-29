from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_impact_metric import ProjectImpactMetric


class ImpactMetricRepository:
    """Database access for project impact metrics.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.

    Every metric lookup is scoped by (metric_id, project_id): a metric that
    belongs to another project is invisible through this repository, so a
    metric of Project A can never be modified or deleted through Project B's
    URL (the caller sees 404, not the row).
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> ProjectImpactMetric:
        metric = ProjectImpactMetric(**data)
        self.db.add(metric)
        self.db.flush()
        return metric

    def get_in_project(
        self, metric_id: UUID, project_id: UUID
    ) -> ProjectImpactMetric | None:
        return self.db.execute(
            select(ProjectImpactMetric).where(
                ProjectImpactMetric.id == metric_id,
                ProjectImpactMetric.project_id == project_id,
            )
        ).scalar_one_or_none()

    def list_for_project(self, project_id: UUID) -> list[ProjectImpactMetric]:
        return list(
            self.db.execute(
                select(ProjectImpactMetric)
                .where(ProjectImpactMetric.project_id == project_id)
                .order_by(ProjectImpactMetric.created_at.asc())
            )
            .scalars()
            .all()
        )

    def update(self, metric: ProjectImpactMetric, data: dict) -> ProjectImpactMetric:
        for key, value in data.items():
            setattr(metric, key, value)
        self.db.flush()
        return metric

    def delete(self, metric: ProjectImpactMetric) -> None:
        self.db.delete(metric)
        self.db.flush()