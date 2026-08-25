from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.discovery import ProblemDnaSummary
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/api/challenges", tags=["problem-dna"])


def get_challenge_service(db: Session = Depends(get_db)) -> ChallengeService:
    return ChallengeService(db)


@router.get("/{challenge_id}/related")
def get_related_challenges(
    challenge_id: UUID,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    service: ChallengeService = Depends(get_challenge_service),
):
    """Related challenges derived from reliable Problem DNA (deterministic).

    Only challenges whose DNA meets the minimum-confidence threshold are
    suggested; every item carries human-readable evidence for why it is
    related. Returns an empty list when no reliable relationships exist.
    """
    related = service.get_related(challenge_id, limit=limit)
    return {
        "items": [
            {
                "challenge": {
                    "id": str(rc.challenge.id),
                    "title": rc.challenge.title,
                    "location": rc.challenge.location,
                    "status": rc.challenge.status.value,
                    "created_at": rc.challenge.created_at.isoformat(),
                },
                "dna": ProblemDnaSummary.model_validate(rc.dna).model_dump(mode="json"),
                "score": rc.score,
                "reasons": rc.reasons,
            }
            for rc in related
        ]
    }
