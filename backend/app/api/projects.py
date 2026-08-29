from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.project import (
    ProjectDetailResponse,
    ProjectListItem,
    ProjectListQuery,
    ProjectListResponse,
)
from app.schemas.support_offer import (
    SupportOfferCreate,
    SupportOfferResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    query: Annotated[ProjectListQuery, Query()],
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """Public listing of approved solutions (projects).

    Projects exist only for accepted proposals, so this surface is limited to
    approved solutions. No authentication is required to view.
    """
    projects, total = service.list_projects(
        status=query.status, skip=query.skip, limit=query.limit
    )
    return ProjectListResponse(
        items=[ProjectListItem(**p) for p in projects],
        total=total,
        skip=query.skip,
        limit=query.limit,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    """Public detail of an approved project, including its support offers.

    Offers are exposed openly for the demo (org name, support type, message,
    status) so 'industry sees it, team sees offers' is a single surface.
    """
    project = service.get_project(project_id)
    if project is None:
        raise NotFoundError("Project", project_id)
    return ProjectDetailResponse(**project)


@router.post(
    "/{project_id}/offers",
    response_model=SupportOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_offer(
    project_id: UUID,
    payload: SupportOfferCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> SupportOfferResponse:
    """Offer support to an approved project.

    Requires an authenticated user who manages an organization (DB-backed).
    The offering organization and offered_by are server-set — a client can
    never forge which organization is offering.
    """
    offer = service.create_offer(
        project_id=project_id,
        support_type=payload.support_type,
        user_id=current_user.id,
        message=payload.message,
    )
    return SupportOfferResponse.model_validate(offer)
