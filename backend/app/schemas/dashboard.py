"""Schemas for the public AIKYRA Impact Dashboard (CP9).

The dashboard is a pure read-only aggregate of already-public surfaces
(institutions, challenges, teams, proposals, projects, support offers,
impact metrics, outcome reports). Every value is a database count/group
computed at request time — nothing is hardcoded. The schema is a stable
contract: the exact top-level key set is asserted by tests.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.project import ProjectStatus


class Ecosystem(BaseModel):
    institutions: int
    challenges_reported: int
    teams_formed: int
    people_engaged: int


class Pipeline(BaseModel):
    challenges_by_status: dict[str, int]
    proposals_submitted: int
    proposals_accepted: int
    projects_by_status: dict[str, int]
    projects_total: int
    outcome_reports: int


class Support(BaseModel):
    organizations: int
    offers_total: int
    offers_by_type: dict[str, int]


class ReportedMetric(BaseModel):
    """A rolled-up total for one allowlisted canonical metric name.

    The `total` is the sum of the metric's values across all projects that
    store a parseable non-negative integer (see DashboardService.CORE_METRICS).
    Entries are only present when at least one value was safely summable, so
    a missing entry means "no data" rather than "zero impact".
    """

    name: str
    unit: str | None
    total: int


class RecentProjectMetric(BaseModel):
    """A project's impact metric echoed verbatim from the database.

    `value` is the original CP7 string ('120', '~85%', '4x', 'High') —
    never converted, never exaggerated, never parsed into a number.
    """

    name: str
    value: str
    unit: str | None


class RecentProject(BaseModel):
    """One of the (max 5) most recently implemented projects, with its
    verbatim impact evidence."""

    project_id: UUID
    title: str
    status: ProjectStatus
    metrics: list[RecentProjectMetric]


class Impact(BaseModel):
    metrics_total: int
    projects_reporting: int
    projects_with_report: int
    reported_metrics: list[ReportedMetric]
    recent_implemented: list[RecentProject]


class DashboardResponse(BaseModel):
    ecosystem: Ecosystem
    pipeline: Pipeline
    support: Support
    impact: Impact
    generated_at: datetime