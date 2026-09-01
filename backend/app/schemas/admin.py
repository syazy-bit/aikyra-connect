"""Schemas for admin dashboard endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.challenge import ChallengeStatus
from app.models.problem_dna import DnaValidationStatus, UrgencyLevel
from app.models.institution import InstitutionVerificationStatus, InstitutionType


class AdminOverviewResponse(BaseModel):
    """Aggregated counts for admin overview page."""

    model_config = ConfigDict(from_attributes=True)

    problems_awaiting_review: int
    dna_needing_validation: int
    institutions_pending_verification: int
    verified_institutions: int


class AdminProblemDnaSummary(BaseModel):
    """Lightweight DNA projection for admin review queue."""

    model_config = ConfigDict(from_attributes=True)

    primary_domain: Optional[str]
    urgency: UrgencyLevel
    confidence_score: Optional[float]
    validation_status: DnaValidationStatus


class AdminChallengeListItem(BaseModel):
    """Challenge item for admin review queue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    location: str
    status: ChallengeStatus
    created_at: datetime
    updated_at: datetime
    dna: Optional["AdminProblemDnaSummary"] = None


class AdminChallengeDetailResponse(BaseModel):
    """Full challenge detail for admin review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str
    status: ChallengeStatus
    created_at: datetime
    updated_at: datetime
    image_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dna: Optional["AdminProblemDnaDetail"] = None


class AdminProblemDnaDetail(BaseModel):
    """Full DNA detail for admin review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    primary_domain: Optional[str]
    secondary_domains: list[str]
    subdomain: Optional[str]
    problem_type: Optional[str]
    geographic_context: Optional[str]
    urgency: UrgencyLevel
    affected_stakeholders: list[str]
    keywords: list[str]
    required_expertise: list[str]
    potential_solution_areas: list[str]
    confidence_score: Optional[float]
    signals: dict[str, list[str]]
    generated_by: str
    analyzer_version: str
    validation_status: DnaValidationStatus
    validated_at: Optional[datetime]
    validated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class ChallengeStatusTransitionRequest(BaseModel):
    """Request to transition challenge status."""

    status: ChallengeStatus
    note: Optional[str] = None


class DNAValidationRequest(BaseModel):
    """Request to validate/update Problem DNA."""

    primary_domain: Optional[str] = None
    urgency: Optional[UrgencyLevel] = None
    validation_status: DnaValidationStatus
    note: Optional[str] = None


class AdminInstitutionListItem(BaseModel):
    """Institution item for admin review queue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    institution_type: InstitutionType
    location: str
    verification_status: InstitutionVerificationStatus
    verified_at: Optional[datetime]
    verified_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class AdminInstitutionListResponse(BaseModel):
    items: list[AdminInstitutionListItem]
    total: int
    skip: int
    limit: int


# Update forward references
AdminChallengeListItem.model_rebuild()
AdminChallengeDetailResponse.model_rebuild()


class AdminInstitutionListQuery(BaseModel):
    """Validated query parameters for admin institution listing."""

    verification_status: Optional[InstitutionVerificationStatus] = None
    institution_type: Optional[InstitutionType] = None
    skip: int = 0
    limit: int = 20