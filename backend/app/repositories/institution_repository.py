from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.institution import Institution


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalized_name_expr():
    """Normalized-name expression — must stay byte-identical to the
    `uq_institutions_name_normalized` index expression in the Phase 4A
    migration so the service-level duplicate pre-check mirrors the DB
    constraint exactly."""
    cleaned = func.regexp_replace(
        func.regexp_replace(Institution.name, "[^a-zA-Z0-9]+", " ", "g"),
        r"\s+",
        " ",
        "g",
    )
    return func.lower(func.btrim(cleaned))


class InstitutionRepository:
    """Database access for institutions.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> Institution:
        institution = Institution(**data)
        self.db.add(institution)
        self.db.flush()
        return institution

    def get_by_id(self, institution_id: UUID) -> Institution | None:
        return self.db.get(Institution, institution_id)

    def get_by_exact_normalized_name(self, normalized_name: str) -> Institution | None:
        """Match on the same expression as the DB unique index so the
        service-level pre-check mirrors the database constraint."""
        return self.db.execute(
            select(Institution).where(
                normalized_name_expr() == normalized_name
            )
        ).scalar_one_or_none()

    def find_by_website_substring(self, host_substring: str) -> list[Institution]:
        """Cheap case-insensitive pre-filter over stored websites.

        Returns candidates whose website contains the host substring;
        exact host equality (scheme/path-insensitive) is confirmed by the
        service layer via URL parsing.
        """
        pattern = f"%{_escape_like(host_substring.lower())}%"
        result = self.db.execute(
            select(Institution).where(
                Institution.website.is_not(None),
                func.lower(Institution.website).like(pattern, escape="\\"),
            )
        )
        return list(result.scalars().all())

    def update(self, institution: Institution, data: dict) -> Institution:
        for field, value in data.items():
            setattr(institution, field, value)
        self.db.flush()
        return institution

    @staticmethod
    def _apply_filters(stmt, *, q, types, domains):
        if q:
            stmt = stmt.where(
                Institution.search_vector.bool_op("@@")(
                    func.websearch_to_tsquery("english", q)
                )
            )
        if types:
            stmt = stmt.where(Institution.institution_type.in_(types))
        if domains:
            # Containment (@>) per requested slug, OR-ed together —
            # supported by the jsonb_path_ops GIN index on domains.
            conditions = [
                Institution.domains.contains([slug]) for slug in domains
            ]
            stmt = stmt.where(or_(*conditions))
        return stmt

    @staticmethod
    def _order_by(stmt, sort: str, ts_query):
        if sort == "oldest":
            return stmt.order_by(Institution.created_at.asc())
        if sort == "relevance" and ts_query is not None:
            rank = func.ts_rank(Institution.search_vector, ts_query)
            return stmt.order_by(rank.desc(), Institution.created_at.desc())
        return stmt.order_by(Institution.created_at.desc())

    def list_institutions(
        self,
        *,
        q: str | None = None,
        types: list | None = None,
        domains: list[str] | None = None,
        sort: str = "newest",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Institution], int]:
        ts_query = (
            func.websearch_to_tsquery("english", q)
            if sort == "relevance" and q
            else None
        )
        stmt = self._apply_filters(
            select(Institution), q=q, types=types, domains=domains
        )
        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        ordered = self._order_by(stmt, sort, ts_query)
        rows = self.db.execute(ordered.offset(skip).limit(limit)).scalars().all()
        return list(rows), total
