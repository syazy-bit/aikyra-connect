"""Read-only aggregation for the public AIKYRA Impact Dashboard (CP9).

Every figure the dashboard returns is computed from live database rows at
request time — nothing is hardcoded, nothing is cached. The service performs
only bounded COUNT/GROUP BY queries over existing tables and stays strictly
read-only (the repository flush/commit discipline does not apply here
because nothing is ever written).

Impact aggregation rules (CP7 stores `value` as a free-form string):
  * Only the names in CORE_METRICS may ever be summed.
  * Only values matching the strict unsigned-integer regex may be summed.
  * Non-numeric values are NEVER guessed, converted or dropped — they stay
    visible verbatim on the recent-implemented cards and still count toward
    the plain metric totals.
No division, percentage or ratio is ever computed.
"""

import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge, ChallengeStatus
from app.models.institution import Institution, InstitutionStatus
from app.models.organization import Organization
from app.models.project import Project, ProjectStatus
from app.models.project_impact_metric import ProjectImpactMetric
from app.models.project_report import ProjectReport
from app.models.proposal import Proposal, ProposalStatus
from app.models.support_offer import SupportOffer, SupportType
from app.models.team import Team, TeamMembership, TeamMembershipStatus, TeamStatus
from app.schemas.dashboard import (
    DashboardResponse,
    Ecosystem,
    Impact,
    Pipeline,
    RecentProject,
    RecentProjectMetric,
    ReportedMetric,
    Support,
)

# Canonical impact metrics whose values MAY be summed across projects
# (name -> display unit). Anything outside this allowlist is never parsed
# or aggregated — it only appears as verbatim project-level evidence.
CORE_METRICS = {
    "Households reached": "households",
    "Villages covered": "villages",
    "Pilot participants": "people",
}

# The only value shapes that may be summed: unsigned integers with optional
# surrounding whitespace ("120", " 85 "). Everything else ("~85%", "4x",
# "High", "12 months") is excluded from sums but remains visible verbatim.
_INTEGER_VALUE = re.compile(r"^\s*\d+\s*$")

# Proposals that were ever submitted, i.e. left the draft/withdrawn states.
# REJECTED still counts as submitted: it reached the review pipeline.
_SUBMITTED_STATUSES = (
    ProposalStatus.SUBMITTED,
    ProposalStatus.UNDER_REVIEW,
    ProposalStatus.ACCEPTED,
    ProposalStatus.REJECTED,
)

RECENT_IMPLEMENTED_LIMIT = 5


class DashboardService:
    """Computes the aggregate public dashboard from the database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Aggregation helpers --------------------------------------------------

    def _count(self, model, where=None) -> int:
        query = select(func.count()).select_from(model)
        if where is not None:
            query = query.where(where)
        return self.db.execute(query).scalar_one()

    def _count_grouped(self, model, column, keys) -> dict[str, int]:
        """Grouped count with every enum member key present (zero-filled)."""
        rows = self.db.execute(select(column, func.count()).group_by(column)).all()
        counts = {status.value: count for status, count in rows}
        return {key.value: counts.get(key.value, 0) for key in keys}

    # --- Sections -------------------------------------------------------------

    def _ecosystem(self) -> Ecosystem:
        people_engaged = self.db.execute(
            select(func.count(func.distinct(TeamMembership.user_id))).where(
                TeamMembership.status == TeamMembershipStatus.ACTIVE
            )
        ).scalar_one()
        return Ecosystem(
            institutions=self._count(
                Institution, Institution.status == InstitutionStatus.ACTIVE
            ),
            challenges_reported=self._count(Challenge),
            teams_formed=self._count(Team, Team.status != TeamStatus.ARCHIVED),
            people_engaged=people_engaged,
        )

    def _pipeline(self) -> Pipeline:
        return Pipeline(
            challenges_by_status=self._count_grouped(
                Challenge, Challenge.status, list(ChallengeStatus)
            ),
            proposals_submitted=self._count(
                Proposal, Proposal.status.in_(_SUBMITTED_STATUSES)
            ),
            proposals_accepted=self._count(
                Proposal, Proposal.status == ProposalStatus.ACCEPTED
            ),
            projects_by_status=self._count_grouped(
                Project, Project.status, list(ProjectStatus)
            ),
            projects_total=self._count(Project),
            outcome_reports=self._count(ProjectReport),
        )

    def _support(self) -> Support:
        return Support(
            organizations=self._count(Organization),
            offers_total=self._count(SupportOffer),
            offers_by_type=self._count_grouped(
                SupportOffer, SupportOffer.support_type, list(SupportType)
            ),
        )

    def _reported_metrics(self) -> list[ReportedMetric]:
        """Roll up only allowlisted metric names whose stored values match
        the strict unsigned-integer regex. Non-matching values are excluded
        from the total but never guessed or dropped from verbatim cards."""
        rows = self.db.execute(
            select(ProjectImpactMetric.name, ProjectImpactMetric.value).where(
                ProjectImpactMetric.name.in_(CORE_METRICS)
            )
        ).all()
        totals: dict[str, int] = {}
        for name, value in rows:
            if _INTEGER_VALUE.match(value):
                totals[name] = totals.get(name, 0) + int(value.strip())
        return [
            ReportedMetric(name=name, unit=unit, total=totals[name])
            for name, unit in CORE_METRICS.items()
            if name in totals
        ]

    def _recent_implemented(self) -> list[RecentProject]:
        """Newest implemented projects (bounded, newest first) with their
        verbatim impact metrics. Always at most RECENT_IMPLEMENTED_LIMIT."""
        projects = (
            self.db.execute(
                select(Project)
                .where(Project.status == ProjectStatus.IMPLEMENTED)
                .order_by(Project.created_at.desc(), Project.id.desc())
                .limit(RECENT_IMPLEMENTED_LIMIT)
            )
            .scalars()
            .all()
        )
        recent = []
        for project in projects:
            metrics = (
                self.db.execute(
                    select(ProjectImpactMetric)
                    .where(ProjectImpactMetric.project_id == project.id)
                    .order_by(
                        ProjectImpactMetric.created_at.asc(),
                        ProjectImpactMetric.id.asc(),
                    )
                )
                .scalars()
                .all()
            )
            recent.append(
                RecentProject(
                    project_id=project.id,
                    title=project.title,
                    status=project.status,
                    metrics=[
                        RecentProjectMetric(name=m.name, value=m.value, unit=m.unit)
                        for m in metrics
                    ],
                )
            )
        return recent

    def _impact(self) -> Impact:
        projects_reporting = self.db.execute(
            select(func.count(func.distinct(ProjectImpactMetric.project_id)))
        ).scalar_one()
        projects_with_report = self.db.execute(
            select(func.count(func.distinct(ProjectReport.project_id)))
        ).scalar_one()
        return Impact(
            metrics_total=self._count(ProjectImpactMetric),
            projects_reporting=projects_reporting,
            projects_with_report=projects_with_report,
            reported_metrics=self._reported_metrics(),
            recent_implemented=self._recent_implemented(),
        )

    # --- Entry point ----------------------------------------------------------

    def get_dashboard(self) -> DashboardResponse:
        return DashboardResponse(
            ecosystem=self._ecosystem(),
            pipeline=self._pipeline(),
            support=self._support(),
            impact=self._impact(),
            generated_at=datetime.now(timezone.utc),
        )