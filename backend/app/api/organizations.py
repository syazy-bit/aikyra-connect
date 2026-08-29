from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.organization import (
    MyOrganizationResponse,
    OrganizationCreate,
    OrganizationResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
def register_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> OrganizationResponse:
    """Register an organization (industry/NGO).

    The authenticated user becomes the organization's manager — resolved from
    the database, never from the client. No onboarding/verification workflow
    in the MVP.
    """
    organization = service.create_organization(
        name=payload.name,
        manager_user_id=current_user.id,
        description=payload.description,
        website=payload.website,
    )
    return OrganizationResponse.model_validate(organization)


@router.get("/me", response_model=MyOrganizationResponse)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> MyOrganizationResponse:
    """Return the caller's managed organization, or None if they manage none."""
    organization = service.get_organization_by_manager(current_user.id)
    if organization is None:
        return MyOrganizationResponse(organization=None)
    return MyOrganizationResponse(
        organization=OrganizationResponse.model_validate(organization)
    )
