from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    """Public aggregate view of the AIKYRA ecosystem.

    No authentication is required: every value is a count/group over
    surfaces that are already public (institutions, challenges, teams,
    proposals, projects, support offers, impact metrics, outcome reports).
    The dashboard never exposes emails, credentials, reviewer data or any
    private information — only aggregate counts and public project evidence.
    """
    return service.get_dashboard()