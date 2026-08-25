from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.challenge import Challenge
from app.repositories.challenge_repository import ChallengeRepository
from app.schemas.challenge import ChallengeCreate, ChallengeUpdate


class ChallengeService:
    """Business logic for challenges.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ChallengeRepository(db)

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

    def list_challenges(self, skip: int = 0, limit: int = 20) -> list[Challenge]:
        return self.repository.get_all(skip=skip, limit=limit)

    def update_challenge(self, challenge_id: UUID, payload: ChallengeUpdate) -> Challenge:
        challenge = self.get_challenge(challenge_id)
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not data:
            return challenge
        updated = self.repository.update(challenge, data)
        self._commit()
        self.db.refresh(updated)
        return updated

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
