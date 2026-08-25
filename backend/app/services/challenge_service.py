from uuid import UUID

from sqlalchemy.orm import Session

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


def _to_list_item(challenge: Challenge, dna) -> ChallengeListItem:
    return ChallengeListItem(
        **ChallengeResponse.model_validate(challenge).model_dump(),
        dna=ProblemDnaSummary.model_validate(dna) if dna is not None else None,
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
        if not data:
            return challenge
        updated = self.repository.update(challenge, data)
        self._commit()
        self.db.refresh(updated)
        return updated

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
        return _to_list_item(challenge, dna)

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
