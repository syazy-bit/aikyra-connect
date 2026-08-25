from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.problem_dna import DnaSource, DnaValidationStatus, ProblemDna
from app.repositories.challenge_repository import ChallengeRepository
from app.repositories.problem_dna_repository import ProblemDnaRepository
from app.services.classification import ClassificationResult, RuleBasedClassifier

# DNA below this confidence is flagged needs_review. The baseline grants
# 0.15 confidence per distinct matched taxonomy term (see rule_classifier),
# so this threshold requires >= 3 converging keyword hits: a single generic
# term ("water", "power") is a common false positive and must not pass as
# machine-understood on its own.
LOW_CONFIDENCE_THRESHOLD = 0.45


class ProblemDnaService:
    """Orchestrates challenge analysis into Problem DNA.

    Transaction boundaries are owned here: repositories flush, this service
    commits on success and rolls back on failure.
    """

    def __init__(self, db: Session, classifier: RuleBasedClassifier | None = None) -> None:
        self.db = db
        self.classifier = classifier or RuleBasedClassifier()
        self.dna_repository = ProblemDnaRepository(db)
        self.challenge_repository = ChallengeRepository(db)

    def analyze_challenge(self, challenge_id: UUID) -> tuple[ProblemDna, bool]:
        """Run analysis on a challenge and store the resulting DNA.

        Returns (dna, regenerated). Regeneration overwrites only
        non-validated DNA; validated DNA is protected until a human-edit
        workflow (with authentication) exists.
        """
        challenge = self.challenge_repository.get_by_id(challenge_id)
        if challenge is None:
            raise NotFoundError("Challenge", challenge_id)

        existing = self.dna_repository.get_by_challenge_id(challenge_id)
        if existing is not None and existing.validation_status == DnaValidationStatus.VALIDATED:
            raise ConflictError(
                "Problem DNA for this challenge is already validated "
                "and cannot be overwritten by automated analysis."
            )

        result = self.classifier.classify(
            title=challenge.title,
            description=challenge.description,
            location=challenge.location,
        )
        data = self._to_model_data(result)

        if existing is not None:
            dna = self.dna_repository.update(existing, data)
            regenerated = True
        else:
            dna, regenerated = self._create_protected(challenge_id, data)

        self._commit()
        self.db.refresh(dna)
        return dna, regenerated

    def _create_protected(self, challenge_id: UUID, data: dict) -> tuple[ProblemDna, bool]:
        """Insert new DNA, recovering safely if a concurrent analyze request
        won the race and created the row first (unique constraint on
        challenge_id). The loser re-reads the winner's row and applies the
        same validated-DNA protection before updating it — preserving the
        1:1 constraint without exposing an IntegrityError as a 500.
        """
        try:
            return self.dna_repository.create({"challenge_id": challenge_id, **data}), False
        except IntegrityError:
            self.db.rollback()
            existing = self.dna_repository.get_by_challenge_id(challenge_id)
            if existing is None:
                # Challenge (and its DNA) vanished mid-race via cascade delete.
                raise NotFoundError("Challenge", challenge_id) from None
            if existing.validation_status == DnaValidationStatus.VALIDATED:
                raise ConflictError(
                    "Problem DNA for this challenge is already validated "
                    "and cannot be overwritten by automated analysis."
                ) from None
            return self.dna_repository.update(existing, data), True

    def get_dna(self, challenge_id: UUID) -> ProblemDna:
        if self.challenge_repository.get_by_id(challenge_id) is None:
            raise NotFoundError("Challenge", challenge_id)
        dna = self.dna_repository.get_by_challenge_id(challenge_id)
        if dna is None:
            raise NotFoundError("Problem DNA for challenge", challenge_id)
        return dna

    @staticmethod
    def _to_model_data(result: ClassificationResult) -> dict:
        return {
            "primary_domain": result.primary_domain,
            "secondary_domains": result.secondary_domains,
            "subdomain": result.subdomain,
            "problem_type": result.problem_type,
            "geographic_context": result.geographic_context,
            "urgency": result.urgency,
            "affected_stakeholders": result.affected_stakeholders,
            "keywords": result.keywords,
            "required_expertise": result.required_expertise,
            "potential_solution_areas": result.potential_solution_areas,
            "confidence_score": result.confidence_score,
            "signals": result.signals,
            "generated_by": DnaSource.DETERMINISTIC_BASELINE,
            "analyzer_version": RuleBasedClassifier.VERSION,
            "validation_status": (
                DnaValidationStatus.NEEDS_REVIEW
                if result.primary_domain is None
                or result.confidence_score < LOW_CONFIDENCE_THRESHOLD
                else DnaValidationStatus.PENDING_VALIDATION
            ),
            "validated_at": None,
        }

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
