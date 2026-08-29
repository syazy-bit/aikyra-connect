"""Schemas for the public Community Funding surface (AIKYRA VERIFIED FUNDING).

Every numeric field is computed by the service from COMPLETED contributions
stored as integer minor units (paise); no value originates from a client.
progress_bp is a basis-point progress (0-10000) so percentages render without
floating point. status is one of OPEN / FULLY_FUNDED / CLOSED, where
FULLY_FUNDED is derived from the money math (raised >= goal) — never stored.
"""

from uuid import UUID

from pydantic import BaseModel


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