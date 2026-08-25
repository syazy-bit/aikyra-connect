from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.text import extract_location_tokens
from app.models.challenge import Challenge, ChallengeStatus
from app.models.problem_dna import ProblemDna, UrgencyLevel


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DiscoveryRepository:
    """Read-side query construction for challenge discovery.

    Read-only: no transaction management lives here. Uses a LEFT JOIN so
    challenges without DNA remain visible in every browsing flow.

    Location matching (explainable, deterministic):
      1. The query is normalized into meaningful tokens (lowercased,
         punctuation-stripped, generic stop-words and sub-3-char noise
         removed — see app/core/text.py).
      2. Preferred pass: AND semantics — the stored location must contain
         every meaningful token.
      3. Fallback (only when the preferred pass is empty): challenges
         containing at least one meaningful token, ranked by matched-token
         count DESC, then created_at DESC.
      4. Queries with no meaningful tokens match nothing — generic or
         junk input can never broaden the result set.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return select(Challenge, ProblemDna).outerjoin(
            ProblemDna, ProblemDna.challenge_id == Challenge.id
        )

    @staticmethod
    def _apply_filters(stmt, *, domains, urgencies, statuses, has_dna, q):
        if q:
            stmt = stmt.where(
                Challenge.search_vector.bool_op("@@")(
                    func.websearch_to_tsquery("english", q)
                )
            )
        if domains:
            stmt = stmt.where(ProblemDna.primary_domain.in_(domains))
        if urgencies:
            stmt = stmt.where(ProblemDna.urgency.in_(urgencies))
        if statuses:
            stmt = stmt.where(Challenge.status.in_(statuses))
        if has_dna is True:
            stmt = stmt.where(ProblemDna.id.is_not(None))
        elif has_dna is False:
            stmt = stmt.where(ProblemDna.id.is_(None))
        return stmt

    @staticmethod
    def _token_contains(token: str):
        return Challenge.location.ilike(f"%{_escape_like(token)}%", escape="\\")

    @classmethod
    def _location_all_tokens_condition(cls, tokens: set[str]):
        return and_(*(cls._token_contains(token) for token in sorted(tokens)))

    @classmethod
    def _location_match_count(cls, tokens: set[str]):
        expr = None
        for token in sorted(tokens):
            term = case((cls._token_contains(token), 1), else_=0)
            expr = term if expr is None else expr + term
        return expr

    @staticmethod
    def _order_by(stmt, sort: str, ts_query):
        if sort == "oldest":
            return stmt.order_by(Challenge.created_at.asc())
        if sort == "urgency":
            urgency_rank = case(
                (ProblemDna.urgency == UrgencyLevel.CRITICAL, 4),
                (ProblemDna.urgency == UrgencyLevel.HIGH, 3),
                (ProblemDna.urgency == UrgencyLevel.MEDIUM, 2),
                (ProblemDna.urgency == UrgencyLevel.LOW, 1),
                else_=0,
            )
            return stmt.order_by(urgency_rank.desc(), Challenge.created_at.desc())
        if sort == "relevance" and ts_query is not None:
            rank = func.ts_rank(Challenge.search_vector, ts_query)
            return stmt.order_by(rank.desc(), Challenge.created_at.desc())
        return stmt.order_by(Challenge.created_at.desc())

    def _count(self, stmt) -> int:
        return self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()

    def _page(self, stmt, skip: int, limit: int) -> list[tuple[Challenge, ProblemDna | None]]:
        rows = self.db.execute(stmt.offset(skip).limit(limit)).all()
        return [(row[0], row[1]) for row in rows]

    def discover(
        self,
        *,
        q: str | None = None,
        domains: list[str] | None = None,
        urgencies: list[UrgencyLevel] | None = None,
        statuses: list[ChallengeStatus] | None = None,
        location: str | None = None,
        has_dna: bool | None = None,
        sort: str = "newest",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Challenge, ProblemDna | None]], int]:
        ts_query = (
            func.websearch_to_tsquery("english", q)
            if sort == "relevance" and q
            else None
        )
        stmt = self._apply_filters(
            self._base_query(),
            domains=domains,
            urgencies=urgencies,
            statuses=statuses,
            has_dna=has_dna,
            q=q,
        )

        if location:
            tokens = extract_location_tokens(location)
            if not tokens:
                # Stop-word-only / junk queries never broaden results.
                return [], 0
            strict = stmt.where(self._location_all_tokens_condition(tokens))
            total = self._count(strict)
            if total > 0:
                ordered = self._order_by(strict, sort, ts_query)
                return self._page(ordered, skip, limit), total

            # Deterministic relevance fallback over meaningful tokens only.
            matched_count = self._location_match_count(tokens)
            fallback = stmt.where(matched_count > 0)
            total = self._count(fallback)
            ordered = fallback.order_by(
                matched_count.desc(), Challenge.created_at.desc()
            )
            return self._page(ordered, skip, limit), total

        total = self._count(stmt)
        ordered = self._order_by(stmt, sort, ts_query)
        return self._page(ordered, skip, limit), total

    def get_with_dna(self, challenge_id: UUID) -> tuple[Challenge, ProblemDna | None] | None:
        result = self.db.execute(
            self._base_query().where(Challenge.id == challenge_id)
        ).first()
        return (result[0], result[1]) if result else None

    def related_candidates(
        self, *, exclude_id: UUID, source_domain: str | None, pool_size: int = 200
    ) -> list[tuple[ProblemDna, Challenge]]:
        """Bounded candidate pool for related-challenge scoring.

        Prefers challenges in the same primary domain (index-backed), then
        fills with recent high-confidence DNA from other domains so
        cross-domain keyword relationships are still discoverable. Scoring
        happens in the service layer.
        """
        base = (
            select(ProblemDna, Challenge)
            .join(Challenge, Challenge.id == ProblemDna.challenge_id)
            .where(ProblemDna.challenge_id != exclude_id)
            .where(ProblemDna.confidence_score >= 0.45)
            .where(ProblemDna.primary_domain.is_not(None))
        )
        same_domain = base.where(ProblemDna.primary_domain == source_domain)
        rows = self.db.execute(same_domain).all()
        if len(rows) < pool_size:
            remaining = pool_size - len(rows)
            others = (
                base.where(ProblemDna.primary_domain != source_domain)
                .order_by(ProblemDna.created_at.desc())
                .limit(remaining)
            )
            rows.extend(self.db.execute(others).all())
        return [(row[0], row[1]) for row in rows]
