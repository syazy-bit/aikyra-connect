"""Schemas for project impact metrics (CP7).

Impact is generic and project-specific: name/value/unit are free-form strings
(value stays a string — '120', '~85%', '4x'). Ownership fields (project_id,
team_id, user_id, timestamps) are always server-controlled and rejected here —
a client can never forge which project a metric belongs to or who authored it.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ImpactMetricFields(BaseModel):
    """Shared validation for create/update payloads."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("name", "value")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("unit", "description")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ImpactMetricCreate(_ImpactMetricFields):
    """Payload for creating an impact metric on a project.

    The project is resolved from the URL path, never from the payload;
    project_id, user_id and timestamps are rejected (422).
    """


class ImpactMetricUpdate(_ImpactMetricFields):
    """Payload for editing an impact metric.

    Full edit of the mutable fields (name/value/unit/description); identity
    and ownership fields are rejected (422).
    """


class ImpactMetricResponse(BaseModel):
    """Public projection of a project's impact metric.

    Exposed on the public project detail for the demo — the value/name/unit/
    description are intentionally non-sensitive, so 'everyone sees impact' is
    a single surface like support offers.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    value: str
    unit: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime