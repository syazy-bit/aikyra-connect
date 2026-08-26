from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListQuery,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdate,
)
from app.services.institution_service import InstitutionService

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


def get_institution_service(db: Session = Depends(get_db)) -> InstitutionService:
    return InstitutionService(db)


@router.post(
    "", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED
)
def register_institution(
    payload: InstitutionCreate,
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Register an institution.

    Every registration starts `active` + `unverified` (human-entered data).
    Verification is performed by reviewers in a later phase.
    """
    return service.to_response(service.create_institution(payload))


@router.get("", response_model=InstitutionListResponse)
def list_institutions(
    query: Annotated[InstitutionListQuery, Query()],
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionListResponse:
    """Institution listing foundation: search, type/domain filters, sorting,
    pagination."""
    return service.list_institutions(query)


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: UUID,
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Full institution profile including capability data."""
    return service.to_response(service.get_institution(institution_id))


@router.patch("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: UUID,
    payload: InstitutionUpdate,
    service: InstitutionService = Depends(get_institution_service),
) -> InstitutionResponse:
    """Partial profile/capability update (replace-whole semantics for the
    capabilities object).

    Verification/lifecycle fields are intentionally excluded from this
    payload — they are trust/workflow fields owned by reviewers with roles
    (added in a later phase). Until authentication exists, mutation
    endpoints are open by documented design; no fake ownership checks.
    """
    return service.to_response(service.update_institution(institution_id, payload))
