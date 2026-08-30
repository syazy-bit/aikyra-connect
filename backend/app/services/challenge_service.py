from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.challenge import Challenge
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.discovery_repository import DiscoveryRepository
from app.schemas.challenge import ChallengeCreate, ChallengeResponse, ChallengeUpdate
from app.schemas.discovery import (
    ChallengeDetailResponse,
    ChallengeListItem,
    ChallengeListResponse,
    DiscoveryQuery,
    ProblemDnaSummary,
)
from app.services.related_challenge_service import (
    RelatedChallenge,
    is_eligible,
    score_candidate,
)
from app.utils.image_storage import ImageStorage, LocalFileStorage


def _to_list_item(challenge: Challenge, dna) -> ChallengeListItem:
    return ChallengeListItem(
        **ChallengeResponse.model_validate(challenge).model_dump(),
        dna=ProblemDnaSummary.model_validate(dna) if dna is not None else None,
    )


def _to_detail_item(challenge: Challenge, dna) -> ChallengeDetailResponse:
    """Detail item: the only shape that exposes precise coordinates, which
    power the public "View on map" link."""
    return ChallengeDetailResponse(
        **ChallengeResponse.model_validate(challenge).model_dump(),
        dna=ProblemDnaSummary.model_validate(dna) if dna is not None else None,
        latitude=challenge.latitude,
        longitude=challenge.longitude,
    )


class ChallengeService:
    """Business logic for challenges.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ChallengeRepository(db)
        self.discovery_repository = DiscoveryRepository(db)
        self.storage: ImageStorage = LocalFileStorage(get_settings().uploads_dir)

    # --- Phase 1 CRUD -------------------------------------------------

    def create_challenge(self, payload: ChallengeCreate) -> Challenge:
        challenge = self.repository.create(payload.model_dump())
        self._commit()
        self.db.refresh(challenge)
        return challenge

    def get_challenge(self, challenge_id: UUID) -> Challenge:
        challenge = self.repository.get_by_id(challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge", challenge_id)
        return challenge

    def update_challenge(self, challenge_id: UUID, payload: ChallengeUpdate) -> Challenge:
        challenge = self.get_challenge(challenge_id)
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        # Coordinates are pair-validated upstream. exclude_none would silently
        # drop an explicit clear ({latitude: null, longitude: null}), so carry
        # them through explicitly so a clear request persists.
        if {"latitude", "longitude"} <= set(payload.model_fields_set):
            data["latitude"] = payload.latitude
            data["longitude"] = payload.longitude
        if not data:
            return challenge
        updated = self.repository.update(challenge, data)
        self._commit()
        self.db.refresh(updated)
        return updated

    # --- Photo evidence (public, optional, single image) --------------------

    def upload_image(self, challenge_id: UUID, data: bytes) -> Challenge:
        """Attach an optional public photo to a challenge.

        The stored file is uniquely named server-side; the client filename,
        MIME type and extension are never trusted and never used as a path.
        On a failed upload (validation/storage error) the existing valid image
        is left untouched. The existing image is removed only after the new
        reference is durably committed.
        """
        challenge = self.get_challenge(challenge_id)
        new_reference = self.storage.store(data)  # raises ImageValidationError
        old_reference = challenge.image_path
        try:
            self.repository.set_image_path(challenge, new_reference)
            self._commit()
        except Exception:
            # Rollback leaves the DB pointing at the old image; remove the new
            # orphan file so we never leak disk.
            self.storage.delete(new_reference)
            raise
        if old_reference:
            self.storage.delete(old_reference)
        self.db.refresh(challenge)
        return challenge

    def get_image(self, challenge_id: UUID) -> tuple[bytes, str]:
        """Return (bytes, content_type) for a challenge's public evidence.

        Raises NotFoundError when the challenge or its image does not exist.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge.image_path:
            raise NotFoundError("Image", challenge_id)
        try:
            return self.storage.read(challenge.image_path)
        except (FileNotFoundError, ValueError) as exc:
            raise NotFoundError("Image", challenge_id) from exc

    # --- Phase 3 discovery --------------------------------------------

    def discover(self, query: DiscoveryQuery) -> ChallengeListResponse:
        rows, total = self.discovery_repository.discover(
            q=query.q,
            domains=query.domains or None,
            urgencies=list(query.urgencies) or None,
            location=query.location,
            has_dna=query.has_dna,
            sort=query.sort.value,
            skip=query.skip,
            limit=query.limit,
        )
        items = [_to_list_item(challenge, dna) for challenge, dna in rows]
        return ChallengeListResponse(
            items=items, total=total, skip=query.skip, limit=query.limit
        )

    def get_challenge_with_dna(self, challenge_id: UUID) -> tuple[Challenge, object | None]:
        result = self.discovery_repository.get_with_dna(challenge_id)
        if result is None:
            raise NotFoundError("Challenge", challenge_id)
        return result

    def get_challenge_detail(self, challenge_id: UUID) -> "ChallengeDetailResponse":
        challenge, dna = self.get_challenge_with_dna(challenge_id)
        return _to_detail_item(challenge, dna)

    def get_related(self, challenge_id: UUID, limit: int = 5) -> list[RelatedChallenge]:
        """Deterministic related challenges based on reliable DNA only."""
        source_challenge, source_dna = self.get_challenge_with_dna(challenge_id)
        if not is_eligible(source_dna):
            return []

        candidates = self.discovery_repository.related_candidates(
            exclude_id=challenge_id, source_domain=source_dna.primary_domain
        )

        scored: list[RelatedChallenge] = []
        for candidate_dna, candidate_challenge in candidates:
            if not is_eligible(candidate_dna):
                continue
            score, reasons = score_candidate(
                source_dna, source_challenge, candidate_dna, candidate_challenge
            )
            if reasons:
                scored.append(
                    RelatedChallenge(
                        challenge=candidate_challenge,
                        dna=candidate_dna,
                        score=score,
                        reasons=reasons,
                    )
                )
        scored.sort(key=lambda rc: (-rc.score, rc.challenge.created_at), )
        return scored[:limit]

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
