"""Schemas for the public Community Funding surface (AIKYRA VERIFIED FUNDING).

Every numeric field is computed by the service from COMPLETED contributions
stored as integer minor units (paise); no value originates from a client.
progress_bp is a basis-point progress (0-10000) so percentages render without
floating point. status is one of OPEN / FULLY_FUNDED / CLOSED, where
FULLY_FUNDED is derived from the money math (raised >= goal) — never stored.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FundingGoalCreate(BaseModel):
    """Payload for publishing a verified funding goal on a project.

    Only the goal amount (integer minor units) and the mandatory INR currency
    are accepted. project_id is taken from the URL path; identity, totals,
    supporter counts, status and every other field are rejected (422) — the
    client can never forge what belongs to whom or how much exists.
    """

    model_config = ConfigDict(extra="forbid")

    goal_minor: int = Field(gt=0, le=9223372036854775807, description="Goal amount in paise (integer minor units)")
    currency: Literal["INR"] = "INR"


class FundingGoalUpdate(BaseModel):
    """Payload for editing a verified funding goal.

    Only goal_minor is editable and only while the goal is OPEN — currency is
    permanently INR, project_id is never changeable, and totals/status/identity
    fields are rejected (422). The service forbids lowering the goal below the
    already-raised completed amount (409).
    """

    model_config = ConfigDict(extra="forbid")

    goal_minor: int = Field(gt=0, le=9223372036854775807, description="Goal amount in paise (integer minor units)")


class FundingSummary(BaseModel):
    """Server-derived funding summary for one approved solution.

    Contains only aggregate, public numbers: no contributions, no supporter
    accounts/names/amounts, no emails, no timestamps of individual pledges.
    """

    project_id: UUID
    goal_minor: int
    raised_minor: int
    remaining_minor: int
    currency: str
    progress_bp: int
    supporter_count: int
    status: str


class FundingResponse(BaseModel):
    """Public read of a project's funding.

    `funding` is null when the project has no verified funding goal — a safe
    empty response, never fabricated zeros.
    """

    project_id: UUID
    funding: FundingSummary | None