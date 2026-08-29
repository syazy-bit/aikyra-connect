"""Schemas for industry/NGO organizations (support offering)."""

from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationCreate(BaseModel):
    """Payload for registering an organization.

    The manager relationship (`manager_user_id`) is always server-set from
    the authenticated caller — never accepted from the client. There is no
    onboarding/verification workflow in the MVP.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=5000)
    website: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("description")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("website")
    @classmethod
    def _validate_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or whitespace")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be a valid absolute http(s) URL")
        return value


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    website: str | None
    manager_user_id: UUID
    created_at: datetime
    updated_at: datetime


class MyOrganizationResponse(BaseModel):
    """The caller's managed organization, or None if they manage none."""

    organization: OrganizationResponse | None = None
