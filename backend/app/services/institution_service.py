import re
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.institution import (
    Institution,
    InstitutionStatus,
    InstitutionVerificationStatus,
)
from app.repositories.institution_repository import InstitutionRepository
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListQuery,
    InstitutionListResponse,
    InstitutionListItem,
    InstitutionResponse,
    InstitutionUpdate,
)

# Normalization for service-level duplicate detection — byte-equivalent to
# the `uq_institutions_name_normalized` index expression (case-fold, trim,
# punctuation collapsed to spaces, whitespace runs squeezed). One indexed
# lookup is therefore authoritative; the DB index remains the race guard.
_PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_institution_name(name: str) -> str:
    without_punctuation = _PUNCTUATION_PATTERN.sub(" ", name.lower())
    return _WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def extract_website_host(website: str | None) -> str | None:
    if not website:
        return None
    host = urlparse(website).netloc.lower()
    return host or None


def _drop_empty_sections(capabilities: dict[str, list[str]]) -> dict[str, list[str]]:
    """Persist only populated capability sections so stored JSON stays
    meaningful. Sections are additive over time."""
    return {section: items for section, items in capabilities.items() if items}


# Message used when the database-level unique constraint fires after an
# application-level pre-check has already passed (concurrent registration).
# No existing-row id is available in this path.
_RACE_DUPLICATE_NAME_MESSAGE = "An institution with this name already exists."


class InstitutionService:
    """Business logic for institutions.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.

    Trust model (Phase 4A): every registration is human-entered data that
    starts `active` + `unverified`. Verification transitions are owned by
    reviewers with roles in a later phase — nothing here may verify an
    institution. Only `active` + `verified` institutions may participate in
    future matching (Phase 4B gate).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InstitutionRepository(db)

    # --- Registration ---------------------------------------------------

    def create_institution(self, payload: InstitutionCreate) -> Institution:
        self._ensure_name_available(payload.name)
        self._ensure_website_host_available(payload.website)
        try:
            institution = self.repository.create(
                {
                    **payload.model_dump(),
                    "capabilities": _drop_empty_sections(
                        payload.capabilities.model_dump()
                    ),
                    "status": InstitutionStatus.ACTIVE,
                    "verification_status": InstitutionVerificationStatus.UNVERIFIED,
                }
            )
            self._commit()
        except IntegrityError:
            # Race-safe duplicate protection: the application-level
            # pre-checks above are inherently race-prone. The database
            # unique constraint (uq_institutions_name_normalized) is the
            # final source of truth — a lost race surfaces here as an
            # IntegrityError and must translate into a domain-level 409
            # conflict, never a 500. The transaction is rolled back before
            # the ConflictError propagates.
            self.db.rollback()
            raise ConflictError(_RACE_DUPLICATE_NAME_MESSAGE) from None
        self.db.refresh(institution)
        return institution

    # --- Retrieval --------------------------------------------------------

    def get_institution(self, institution_id: UUID) -> Institution:
        institution = self.repository.get_by_id(institution_id)
        if institution is None:
            raise NotFoundError("Institution", institution_id)
        return institution

    # --- Update -----------------------------------------------------------

    def update_institution(
        self, institution_id: UUID, payload: InstitutionUpdate
    ) -> Institution:
        institution = self.get_institution(institution_id)
        data = payload.model_dump(exclude_unset=True, exclude_none=True)

        if "name" in data:
            self._ensure_name_available(data["name"], exclude_id=institution.id)
        if "website" in data:
            self._ensure_website_host_available(
                data["website"], exclude_id=institution.id
            )

        if not data:
            return institution

        if "capabilities" in data:
            data["capabilities"] = _drop_empty_sections(data["capabilities"])

        try:
            updated = self.repository.update(institution, data)
            self._commit()
        except IntegrityError:
            # Same race protection as registration: a concurrent create can
            # take the normalized name between the pre-check above and this
            # write. Roll back cleanly and report a structured conflict.
            self.db.rollback()
            raise ConflictError(_RACE_DUPLICATE_NAME_MESSAGE) from None
        self.db.refresh(updated)
        return updated

    # --- Listing ------------------------------------------------------------

    def list_institutions(self, query: InstitutionListQuery) -> InstitutionListResponse:
        rows, total = self.repository.list_institutions(
            q=query.q,
            types=list(query.types) or None,
            domains=query.domains or None,
            sort=query.sort.value,
            skip=query.skip,
            limit=query.limit,
        )
        items = [InstitutionListItem.model_validate(row) for row in rows]
        return InstitutionListResponse(
            items=items, total=total, skip=query.skip, limit=query.limit
        )

    # --- Duplicate protection -------------------------------------------------

    def _ensure_name_available(self, name: str, exclude_id: UUID | None = None) -> None:
        normalized = normalize_institution_name(name)
        existing = self.repository.get_by_exact_normalized_name(normalized)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(
                "An institution with this name already exists "
                f"(id: {existing.id})."
            )

    def _ensure_website_host_available(
        self, website: str | None, exclude_id: UUID | None = None
    ) -> None:
        host = extract_website_host(website)
        if host is None:
            return
        candidates = self.repository.find_by_website_substring(host)
        for candidate in candidates:
            if candidate.id == exclude_id:
                continue
            if extract_website_host(candidate.website) == host:
                raise ConflictError(
                    "An institution with this website already exists "
                    f"(id: {candidate.id})."
                )

    # --- Serialization helpers -----------------------------------------------

    @staticmethod
    def to_response(institution: Institution) -> InstitutionResponse:
        return InstitutionResponse.model_validate(institution)

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
