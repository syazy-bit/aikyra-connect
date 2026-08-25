from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
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


@router.get("", response_model=list[ChallengeResponse])
def list_challenges(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: ChallengeService = Depends(get_challenge_service),
) -> list[ChallengeResponse]:
    challenges = service.list_challenges(skip=skip, limit=limit)
    return [ChallengeResponse.model_validate(c) for c in challenges]


@router.get("/{challenge_id}", response_model=ChallengeResponse)
def get_challenge(
    challenge_id: UUID,
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeResponse:
    return ChallengeResponse.model_validate(service.get_challenge(challenge_id))


@router.patch("/{challenge_id}", response_model=ChallengeResponse)
def update_challenge(
    challenge_id: UUID,
    payload: ChallengeUpdate,
    service: ChallengeService = Depends(get_challenge_service),
) -> ChallengeResponse:
    return ChallengeResponse.model_validate(service.update_challenge(challenge_id, payload))
