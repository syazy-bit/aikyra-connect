"""Schemas for support offers (industry/NGO -> approved project)."""

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.support_offer import SupportOfferStatus, SupportType


class SupportOfferCreate(BaseModel):
    """Payload for offering support to an approved project.

    organization_id, offered_by and status are always server-controlled from
    the authenticated organization manager and rejected here — a client can
    never forge which organization is offering or the offer's state.
    """

    model_config = ConfigDict(extra="forbid")

    support_type: SupportType
    message: str | None = Field(default=None, max_length=20000)

    @field_validator("message")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SupportOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    organization_id: UUID
    offered_by: UUID
    support_type: SupportType
    message: str | None
    status: SupportOfferStatus
    created_at: datetime
    updated_at: datetime
