"""Schemas for Phase 4C authentication."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty or whitespace")
    return value


class AuthRegister(BaseModel):
    """User registration payload."""

    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=250)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.fullmatch(pattern, value):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_non_empty(value) or None


class AuthLogin(BaseModel):
    """User login payload."""

    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthRegisterResponse(BaseModel):
    """Response after successful registration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    created_at: datetime


class AuthLoginResponse(BaseModel):
    """Response after successful login."""

    access_token: str
    token_type: str = "bearer"


class AuthMeResponse(BaseModel):
    """Response for GET /api/auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime
