"""Schemas for project outcome reports (CP8).

The report is the conclusive, publicly readable narrative for an implemented
project. Ownership fields (project_id, team_id, user_id, timestamps) are always
server-controlled and rejected here — a client can never forge which project a
report belongs to or who wrote it. The report is created via the project URL
only; there is no separate report-ID route.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

REPORT_MAX_TEXT = 20_000


class _ReportFields(BaseModel):
    """Shared validation for create/update payloads."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=REPORT_MAX_TEXT)
    results: str | None = Field(default=None, min_length=1, max_length=REPORT_MAX_TEXT)
    lessons_learned: str | None = Field(
        default=None, min_length=1, max_length=REPORT_MAX_TEXT
    )
    next_steps: str | None = Field(
        default=None, min_length=1, max_length=REPORT_MAX_TEXT
    )

    @field_validator("summary")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("results", "lessons_learned", "next_steps")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProjectReportCreate(_ReportFields):
    """Payload for writing the outcome report on an implemented project.

    The project is resolved from the URL path; project_id, submitted_by and
    timestamps are rejected (422).
    """


class ProjectReportUpdate(_ReportFields):
    """Payload for editing an outcome report.

    Full edit of the mutable narrative fields; identity and ownership fields
    are rejected (422).
    """


class ProjectReportResponse(BaseModel):
    """Public projection of a project's outcome report.

    Like impact metrics and support offers, the report is intentionally
    public: it is the final outcome story an institution, backer or citizen
    should be able to read.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    summary: str
    results: str | None
    lessons_learned: str | None
    next_steps: str | None
    created_at: datetime
    updated_at: datetime