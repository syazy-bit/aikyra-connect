from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge


class ChallengeRepository:
    """Database access for challenges.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Challenge:
        challenge = Challenge(**data)
        self.db.add(challenge)
        self.db.flush()
        return challenge

    def get_by_id(self, challenge_id: UUID) -> Challenge | None:
        return self.db.get(Challenge, challenge_id)

    def get_all(self, skip: int = 0, limit: int = 20) -> list[Challenge]:
        result = self.db.execute(
            select(Challenge)
            .order_by(Challenge.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def update(self, challenge: Challenge, data: dict) -> Challenge:
        for field, value in data.items():
            setattr(challenge, field, value)
        self.db.flush()
        return challenge

    def set_image_path(self, challenge: Challenge, image_path: str | None) -> Challenge:
        challenge.image_path = image_path
        self.db.flush()
        return challenge
