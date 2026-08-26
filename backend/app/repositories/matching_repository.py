from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.institution import (
    Institution,
    InstitutionStatus,
    InstitutionVerificationStatus,
)


class MatchingRepository:
    """Read-only candidate selection for the matching engine.

    The eligibility gate (active + verified) is enforced here, in SQL —
    ineligible rows are never fetched, so no response path can leak them.
    Repositories never commit; scoring happens in the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _eligible_stmt(self):
        return select(Institution).where(
            Institution.status == InstitutionStatus.ACTIVE,
            Institution.verification_status
            == InstitutionVerificationStatus.VERIFIED,
        )

    def eligible_candidates(
        self,
        *,
        domain_slugs: list[str] | None = None,
        pool_size: int = 1000,
        min_after_filter: int = 25,
    ) -> tuple[list[Institution], int]:
        """Bounded candidate pool of verified+active institutions.

        Preferred pass: index-backed JSONB containment on any of the DNA
        domains (GIN `ix_institutions_domains`). If that yields too few
        candidates, widen to the full eligible pool so expertise-only or
        location-only matches are not lost.

        Returns (candidates, total_eligible_pool_size).
        """
        base = self._eligible_stmt()
        total_eligible = self.db.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        if domain_slugs:
            filtered = base.where(
                or_(
                    *[Institution.domains.contains([slug]) for slug in domain_slugs]
                )
            )
            rows = list(
                self.db.execute(
                    filtered.order_by(Institution.created_at.desc()).limit(pool_size)
                )
                .scalars()
                .all()
            )
            if len(rows) >= min_after_filter:
                return rows, total_eligible

        rows = list(
            self.db.execute(
                base.order_by(Institution.created_at.desc()).limit(pool_size)
            )
            .scalars()
            .all()
        )
        return rows, total_eligible
