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
from app.models.institution_membership import (
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.repositories.institution_repository import InstitutionRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListQuery,
    InstitutionListResponse,
    InstitutionListItem,
    InstitutionResponse,
    InstitutionUpdate,
    VerificationAction,
    VerificationRequest,
)

from datetime import datetime, timezone


# Normalization for service-level duplicate detection — byte-equivalent to
# the `uq_institutions_name_normalized` index expression (case-fold, trim,
# punctuation collapsed to spaces, whitespace runs squeezed). One indexed
# lookup is therefore authoritative; the DB index remains the race guard.
_PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


# --- Verification state machine -------------------------------------------------
# Maps each action to the set of current statuses from which it is allowed.
_VALID_TRANSITIONS: dict[VerificationAction, set[InstitutionVerificationStatus]] = {
    VerificationAction.SUBMIT_FOR_REVIEW: {
        InstitutionVerificationStatus.UNVERIFIED,
    },
    VerificationAction.VERIFY: {
        InstitutionVerificationStatus.PENDING_REVIEW,
    },
    VerificationAction.REJECT: {
        InstitutionVerificationStatus.PENDING_REVIEW,
    },
    VerificationAction.RESUBMIT: {
        InstitutionVerificationStatus.REJECTED,
    },
    VerificationAction.SUSPEND: {
        InstitutionVerificationStatus.VERIFIED,
    },
    VerificationAction.REINSTATE: {
        InstitutionVerificationStatus.SUSPENDED,
    },
}


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
        self.membership_repository = MembershipRepository(db)

    # --- Registration ---------------------------------------------------

    def create_institution(
        self, payload: InstitutionCreate, institution_admin_user_id: UUID
    ) -> Institution:
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
            self.membership_repository.create(
                {
                    "user_id": institution_admin_user_id,
                    "institution_id": institution.id,
                    "role": InstitutionMembershipRole.INSTITUTION_ADMIN,
                    "status": InstitutionMembershipStatus.ACTIVE,
                }
            )
            self._commit()
        except ConflictError:
            raise
        except IntegrityError:
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

    # --- Membership -------------------------------------------------------

    def get_membership(
        self, user_id: UUID, institution_id: UUID
    ) -> dict | None:
        membership = self.membership_repository.get_membership(
            user_id, institution_id
        )
        if membership is None:
            return None
        role = membership.role.value if hasattr(membership.role, "value") else membership.role
        status_val = membership.status.value if hasattr(membership.status, "value") else membership.status
        return {
            "is_member": True,
            "role": role,
            "membership_status": status_val,
        }

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
            self.db.rollback()
            raise ConflictError(_RACE_DUPLICATE_NAME_MESSAGE) from None
        self.db.refresh(updated)
        return updated

    # --- Verification workflow ------------------------------------------------

    def verify_institution(
        self,
        institution_id: UUID,
        reviewer_user_id: UUID,
        note: str | None = None,
    ) -> Institution:
        """Reviewer verifies a pending institution."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.VERIFY)
        now = datetime.now(timezone.utc)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.VERIFIED,
                "verified_by": reviewer_user_id,
                "verified_at": now,
                "verification_note": note,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def reject_institution(
        self,
        institution_id: UUID,
        reviewer_user_id: UUID,
        note: str | None = None,
    ) -> Institution:
        """Reviewer rejects a pending institution."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.REJECT)
        now = datetime.now(timezone.utc)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.REJECTED,
                "verified_by": reviewer_user_id,
                "verified_at": now,
                "verification_note": note,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def resubmit(
        self,
        institution_id: UUID,
    ) -> Institution:
        """Institution admin/representative resubmits a rejected institution for review."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.RESUBMIT)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.PENDING_REVIEW,
                "verified_by": None,
                "verified_at": None,
                "verification_note": None,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def submit_for_review(
        self,
        institution_id: UUID,
    ) -> Institution:
        """Institution admin/representative submits an unverified institution for review."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.SUBMIT_FOR_REVIEW)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.PENDING_REVIEW,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def suspend_institution(
        self,
        institution_id: UUID,
        reviewer_user_id: UUID,
        note: str | None = None,
    ) -> Institution:
        """Reviewer suspends a verified institution."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.SUSPEND)
        now = datetime.now(timezone.utc)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.SUSPENDED,
                "verified_by": reviewer_user_id,
                "verified_at": now,
                "verification_note": note,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def reinstate_institution(
        self,
        institution_id: UUID,
        reviewer_user_id: UUID,
        note: str | None = None,
    ) -> Institution:
        """Reviewer reinstates a suspended institution."""
        institution = self.get_institution(institution_id)
        self._assert_valid_transition(institution, VerificationAction.REINSTATE)
        now = datetime.now(timezone.utc)
        updated = self.repository.update(
            institution,
            {
                "verification_status": InstitutionVerificationStatus.VERIFIED,
                "verified_by": reviewer_user_id,
                "verified_at": now,
                "verification_note": note,
            },
        )
        self._commit()
        self.db.refresh(updated)
        return updated

    def _assert_valid_transition(
        self,
        institution: Institution,
        action: VerificationAction,
    ) -> None:
        """Raise ConflictError if the current status does not allow this action."""
        allowed = _VALID_TRANSITIONS.get(action, set())
        if institution.verification_status not in allowed:
            raise ConflictError(
                f"Cannot perform '{action.value}' on an institution with "
                f"verification status '{institution.verification_status.value}'."
            )

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
