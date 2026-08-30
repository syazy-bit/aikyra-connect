from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

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
    # Optional precise coordinates. Public once attached, consistent with the
    # public challenge including its text location and photo evidence. Both
    # must be supplied together (pair enforced below); NULL/NULL when absent.
    # allow_inf_nan=False rejects NaN/Infinity literals that the JSON parser
    # would otherwise accept, and ge/le enforce the geographic ranges.
    latitude: float | None = Field(
        default=None, ge=-90, le=90, allow_inf_nan=False
    )
    longitude: float | None = Field(
        default=None, ge=-180, le=180, allow_inf_nan=False
    )

    _validate_title = field_validator("title")(_strip_non_empty)
    _validate_description = field_validator("description")(_strip_non_empty)
    _validate_location = field_validator("location")(_strip_non_empty)

    @model_validator(mode="after")
    def _coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "latitude and longitude must be provided together (or both omitted)"
            )
        return self


class ChallengeUpdate(BaseModel):
    """Public update payload. Status is intentionally excluded — it is a
    workflow field controlled by reviewers with roles (added later)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    latitude: float | None = Field(
        default=None, ge=-90, le=90, allow_inf_nan=False
    )
    longitude: float | None = Field(
        default=None, ge=-180, le=180, allow_inf_nan=False
    )

    @field_validator("title", "location")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def _validate_optional_description(cls, value: str | None) -> str | None:
        return _strip_non_empty(value) if value is not None else None

    @model_validator(mode="after")
    def _coordinate_pair(self):
        # Only enforce the pair rule for fields the caller actually supplied.
        # PATCH with a single coordinate must be rejected, but an empty payload
        # (nothing set) or only non-coordinate fields stay valid.
        supplied = any(
            field in self.model_fields_set for field in ("latitude", "longitude")
        )
        if supplied and (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "latitude and longitude must be provided together (or both omitted)"
            )
        return self


class ChallengeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str
    status: ChallengeStatus
    created_at: datetime
    updated_at: datetime
    # Internal server-generated storage reference. Never serialized — the
    # frontend only needs to know whether public evidence exists.
    image_path: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def has_image(self) -> bool:
        return bool(self.image_path)
