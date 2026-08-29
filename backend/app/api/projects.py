from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.funding import FundingResponse
from app.schemas.impact_metric import (
    ImpactMetricCreate,
    ImpactMetricResponse,
    ImpactMetricUpdate,
)
from app.schemas.project import (
    ProjectDetailResponse,
    ProjectLifecycleUpdate,
    ProjectListItem,
    ProjectListQuery,
    ProjectListResponse,
)
from app.schemas.report import ProjectReportCreate, ProjectReportResponse, ProjectReportUpdate
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


@router.patch("/{project_id}/lifecycle", response_model=ProjectDetailResponse)
def update_project_lifecycle(
    project_id: UUID,
    payload: ProjectLifecycleUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    """Advance the project lifecycle (prototype -> pilot -> implemented).

    Only the active team lead may advance it (authorization resolved from
    the database via the project's team membership). The requested status is
    the whole payload — immutable identity fields are rejected (422). Invalid
    transitions return 409; the project is returned in its updated state.
    """
    project = service.transition_lifecycle(
        project_id=project_id,
        new_status=payload.status,
        user_id=current_user.id,
    )
    return ProjectDetailResponse(**project)


@router.get("/{project_id}/impact", response_model=list[ImpactMetricResponse])
def list_impact_metrics(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> list[ImpactMetricResponse]:
    """Public listing of a project's impact metrics (created_at asc).

    No authentication is required to view: impact is project evidence that
    anyone should be able to read. Unknown project -> 404.
    """
    metrics = service.list_impact_metrics(project_id=project_id)
    return [ImpactMetricResponse.model_validate(m) for m in metrics]


@router.post(
    "/{project_id}/impact",
    response_model=ImpactMetricResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_impact_metric(
    project_id: UUID,
    payload: ImpactMetricCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ImpactMetricResponse:
    """Record an impact metric against a project.

    Only the active team lead may do this (authorization resolved from the
    database via the project's team membership). The project is taken from
    the URL path — project_id/user_id/timestamps are rejected in the schema,
    never accepted from the client.
    """
    metric = service.create_impact_metric(
        project_id=project_id,
        user_id=current_user.id,
        name=payload.name,
        value=payload.value,
        unit=payload.unit,
        description=payload.description,
    )
    return ImpactMetricResponse.model_validate(metric)


@router.patch(
    "/{project_id}/impact/{metric_id}", response_model=ImpactMetricResponse
)
def update_impact_metric(
    project_id: UUID,
    metric_id: UUID,
    payload: ImpactMetricUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ImpactMetricResponse:
    """Edit an impact metric.

    Lead-only, like create. The metric is looked up scoped to the URL's
    project, so a metric belonging to another project is simply not found
    (404) — cross-project modification is impossible. Editing is allowed at
    every lifecycle stage.
    """
    metric = service.update_impact_metric(
        project_id=project_id,
        metric_id=metric_id,
        user_id=current_user.id,
        name=payload.name,
        value=payload.value,
        unit=payload.unit,
        description=payload.description,
    )
    return ImpactMetricResponse.model_validate(metric)


@router.delete(
    "/{project_id}/impact/{metric_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_impact_metric(
    project_id: UUID,
    metric_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Delete an impact metric.

    Lead-only and project-scoped exactly like edit: another project's metric
    is not found (404). Returns 204 with no body.
    """
    service.delete_impact_metric(
        project_id=project_id,
        metric_id=metric_id,
        user_id=current_user.id,
    )


# --- Community funding ----------------------------------------------------

@router.get("/{project_id}/funding", response_model=FundingResponse)
def get_project_funding(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> FundingResponse:
    """Public read of a project's verified community funding.

    No authentication is required. Every number is computed server-side from
    COMPLETED contributions in integer minor units (paise); no totals are ever
    accepted from a client. The response is aggregate-only — individual
    contributions, amounts, supporter accounts and emails are never exposed.
    A project without a verified funding goal returns 200 with
    `funding: null` (a safe empty response, no fabricated zeros). Unknown
    project -> 404.
    """
    return FundingResponse(
        project_id=project_id,
        funding=service.get_public_funding(project_id),
    )


# --- Outcome report (CP8) -------------------------------------------------

@router.get(
    "/{project_id}/report", response_model=ProjectReportResponse
)
def get_project_report(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectReportResponse:
    """Public read of a project's outcome report.

    No authentication is required to view: like impact metrics and support
    offers, the final outcome story is public. The report is project-scoped —
    reached only through the project's URL, never via a standalone report ID.
    Unknown project -> 404; project without a report -> 404.
    """
    report = service.get_project_report(project_id=project_id)
    return ProjectReportResponse.model_validate(report)


@router.post(
    "/{project_id}/report",
    response_model=ProjectReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_report(
    project_id: UUID,
    payload: ProjectReportCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectReportResponse:
    """Write the outcome report for an implemented project.

    Lead-only, and only when the project status is 'implemented' (409
    otherwise). The report is a 1:1 project singleton, so a second report on
    the same project returns 409. All identity/ownership fields are rejected
    in the schema — project_id is taken from the URL path (422 otherwise).
    """
    report = service.create_project_report(
        project_id=project_id,
        user_id=current_user.id,
        summary=payload.summary,
        results=payload.results,
        lessons_learned=payload.lessons_learned,
        next_steps=payload.next_steps,
    )
    return ProjectReportResponse.model_validate(report)


@router.patch(
    "/{project_id}/report", response_model=ProjectReportResponse
)
def update_project_report(
    project_id: UUID,
    payload: ProjectReportUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectReportResponse:
    """Edit the project's outcome report.

    Lead-only, exactly like create. Project-scoped: the URL's project decides
    which report is edited, so another project's report is not reachable. A
    project without a report returns 404.
    """
    report = service.update_project_report(
        project_id=project_id,
        user_id=current_user.id,
        summary=payload.summary,
        results=payload.results,
        lessons_learned=payload.lessons_learned,
        next_steps=payload.next_steps,
    )
    return ProjectReportResponse.model_validate(report)


@router.delete(
    "/{project_id}/report", status_code=status.HTTP_204_NO_CONTENT
)
def delete_project_report(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Delete the project's outcome report.

    Lead-only and project-scoped exactly like edit: a project without a report
    returns 404. Returns 204 with no body on success.
    """
    service.delete_project_report(
        project_id=project_id,
        user_id=current_user.id,
    )
