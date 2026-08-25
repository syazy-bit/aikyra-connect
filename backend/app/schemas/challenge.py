from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.challenge import ChallengeStatus


def _strip_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty or whitespace")
    return value


class ChallengeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    location: str = Field(min_length=1, max_length=200)

    _validate_title = field_validator("title")(_strip_non_empty)
    _validate_description = field_validator("description")(_strip_non_empty)
    _validate_location = field_validator("location")(_strip_non_empty)


class ChallengeUpdate(BaseModel):
    """Public update payload. Status is intentionally excluded — it is a
    workflow field controlled by reviewers with roles (added later)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    location: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("title", "location")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def _validate_optional_description(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None


class ChallengeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str
    status: ChallengeStatus
    created_at: datetime
    updated_at: datetime
