from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.matching import MatchListResponse
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/api/challenges", tags=["matching"])


def get_matching_service(db: Session = Depends(get_db)) -> MatchingService:
    return MatchingService(db)


@router.get("/{challenge_id}/matches", response_model=MatchListResponse)
def get_challenge_matches(
    challenge_id: UUID,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    service: MatchingService = Depends(get_matching_service),
) -> MatchListResponse:
    """Deterministic institution recommendations for a challenge.

    Ranks verified+active institutions against the challenge's reliable
    Problem DNA with a transparent weighted breakdown and human-readable
    reasons. Computed fresh on every request — never persisted, never
    influenced by client-supplied ranking parameters.
    """
    return service.get_matches(challenge_id, skip=skip, limit=limit)
