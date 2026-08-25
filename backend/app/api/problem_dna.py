from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.problem_dna import AnalyzeResponse, ProblemDnaResponse
from app.services.problem_dna_service import ProblemDnaService

router = APIRouter(prefix="/api/challenges", tags=["problem-dna"])


def get_problem_dna_service(db: Session = Depends(get_db)) -> ProblemDnaService:
    return ProblemDnaService(db)


@router.post("/{challenge_id}/analyze", response_model=AnalyzeResponse)
def analyze_challenge(
    challenge_id: UUID,
    service: ProblemDnaService = Depends(get_problem_dna_service),
) -> AnalyzeResponse:
    """Run deterministic analysis and store the challenge's Problem DNA.

    Re-running overwrites non-validated DNA; validated DNA is protected.
    """
    dna, regenerated = service.analyze_challenge(challenge_id)
    return AnalyzeResponse(
        dna=ProblemDnaResponse.model_validate(dna), regenerated=regenerated
    )


@router.get("/{challenge_id}/dna", response_model=ProblemDnaResponse)
def get_challenge_dna(
    challenge_id: UUID,
    service: ProblemDnaService = Depends(get_problem_dna_service),
) -> ProblemDnaResponse:
    return ProblemDnaResponse.model_validate(service.get_dna(challenge_id))
