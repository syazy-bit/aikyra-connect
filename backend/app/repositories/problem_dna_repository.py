from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.problem_dna import ProblemDna


class ProblemDnaRepository:
    """Database access for Problem DNA. Never commits — the service owns
    transaction boundaries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_challenge_id(self, challenge_id: UUID) -> ProblemDna | None:
        result = self.db.execute(
            select(ProblemDna).filter(ProblemDna.challenge_id == challenge_id)
        )
        return result.scalars().first()

    def create(self, data: dict) -> ProblemDna:
        dna = ProblemDna(**data)
        self.db.add(dna)
        self.db.flush()
        return dna

    def update(self, dna: ProblemDna, data: dict) -> ProblemDna:
        for field, value in data.items():
            setattr(dna, field, value)
        self.db.flush()
        return dna
