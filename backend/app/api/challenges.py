from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.schemas.discovery import (
    ChallengeDetailResponse,
    ChallengeListResponse,
    DiscoveryQuery,
)
from app.services.challenge_service import ChallengeService
from app.utils.image_storage import ImageValidationError, MAX_IMAGE_BYTES

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


@router.post(
    "/{challenge_id}/image",
    response_model=ChallengeResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_challenge_image(
    challenge_id: UUID,
    file: UploadFile = File(...),
    service: ChallengeService = Depends(get_challenge_service),
    current_user: User = Depends(get_current_user),
) -> ChallengeResponse:
    """Attach an optional public photo to an existing challenge (authenticated).

    Multipart form field ``file``. Only JPG/PNG/WebP up to 5 MB are accepted.
    The stored filename is generated server-side — the client filename, MIME
    type, extension, and any metadata are never trusted and never used as a
    storage path. Reading a challenge's image is public because challenges are
    public; only the write is authenticated.
    """
    # Cap how much we read into memory to enforce the server-side limit.
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The image is larger than 5 MB. Please upload a smaller photo.",
        )
    try:
        return ChallengeResponse.model_validate(
            service.upload_image(challenge_id, data)
        )
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/{challenge_id}/image")
def get_challenge_image(
    challenge_id: UUID,
    service: ChallengeService = Depends(get_challenge_service),
) -> Response:
    """Return a challenge's public evidence bytes.

    Public, matching the public visibility of the challenge itself. 404 when
    the challenge or its image does not exist.
    """
    content, media_type = service.get_image(challenge_id)
    return Response(content=content, media_type=media_type)
