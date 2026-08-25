from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.schemas.discovery import (
    ChallengeDetailResponse,
    ChallengeListResponse,
    DiscoveryQuery,
)
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


def get_challenge_service(db: Session = Depends(get_db)) -> ChallengeService:
    return ChallengeService(db)


@router.post("", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
def create_challenge(
    payload: ChallengeCreate,
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeResponse:
    return ChallengeResponse.model_validate(service.create_challenge(payload))


@router.get("", response_model=ChallengeListResponse)
def discover_challenges(
    query: Annotated[DiscoveryQuery, Query()],
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeListResponse:
    """Discovery search: pagination, full-text search, DNA filters, sorting."""
    return service.discover(query)


@router.get("/{challenge_id}", response_model=ChallengeDetailResponse)
def get_challenge(
    challenge_id: UUID,
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeDetailResponse:
    """Single challenge with its Problem DNA summary (null when unanalyzed)."""
    return service.get_challenge_detail(challenge_id)


@router.patch("/{challenge_id}", response_model=ChallengeResponse)
def update_challenge(
    challenge_id: UUID,
    payload: ChallengeUpdate,
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeResponse:
    return ChallengeResponse.model_validate(service.update_challenge(challenge_id, payload))
