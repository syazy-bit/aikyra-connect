import enum
import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, Enum, Index, String, Text, func, text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_SEARCH_VECTOR_EXPRESSION = (
    "to_tsvector('english', coalesce(name, '') || ' ' || "
    "coalesce(description, '') || ' ' || coalesce(location, ''))"
)

# Normalized-name uniqueness expression: case-folded, trimmed, punctuation
# collapsed to spaces, internal whitespace runs squeezed to one space.
# Must stay byte-identical to the expression in the Phase 4A migration and
# to InstitutionService.normalize_institution_name().
_NORMALIZED_NAME_EXPRESSION = (
    "lower(btrim(regexp_replace(regexp_replace(name, '[^a-zA-Z0-9]+', ' ', 'g'), "
    "'\\s+', ' ', 'g')))"
)


class InstitutionType(str, enum.Enum):
    UNIVERSITY = "university"
    COLLEGE = "college"
    RESEARCH_INSTITUTE = "research_institute"
    INNOVATION_HUB = "innovation_hub"


class InstitutionStatus(str, enum.Enum):
    """Lifecycle status — operational visibility of the institution record."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class InstitutionVerificationStatus(str, enum.Enum):
    """Trust status — independent from lifecycle.

    Transitions (verify/reject/suspend) are owned by future reviewers with
    roles; Phase 4A only establishes the fields and default state.
    """

    UNVERIFIED = "unverified"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class Institution(Base):
    """A higher-education institution, research institute or innovation hub
    participating in the Aikyra ecosystem.

    Capability data (`domains`, `capabilities`) is 100% human-entered in
    Phase 4A. It is the input surface for the future deterministic matching
    engine (Phase 4B); no matching semantics live here.
    """

    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    institution_type: Mapped[InstitutionType] = mapped_column(
        Enum(
            InstitutionType,
            name="institution_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    # Taxonomy domain slugs this institution can credibly work on.
    # Validated against the controlled taxonomy at every write.
    domains: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Fixed-section capability profile (departments, expertise, research
    # areas, technologies, facilities…). Sections are additive over time.
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[InstitutionStatus] = mapped_column(
        Enum(
            InstitutionStatus,
            name="institution_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=InstitutionStatus.ACTIVE,
        server_default=InstitutionStatus.ACTIVE.value,
    )
    verification_status: Mapped[InstitutionVerificationStatus] = mapped_column(
        Enum(
            InstitutionVerificationStatus,
            name="institution_verification_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=InstitutionVerificationStatus.UNVERIFIED,
        server_default=InstitutionVerificationStatus.UNVERIFIED.value,
    )
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Deliberately NOT a foreign key: the users table does not exist yet.
    # Populated only when the auth/verification phase lands.
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Database-generated full-text search vector (name + description +
    # location). Maintained entirely by PostgreSQL; never written by app code.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(_SEARCH_VECTOR_EXPRESSION, persisted=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_institutions_name_normalized",
            sa_text(_NORMALIZED_NAME_EXPRESSION),
            unique=True,
        ),
        Index("ix_institutions_type", "institution_type"),
        Index("ix_institutions_status", "status"),
        Index("ix_institutions_verification_status", "verification_status"),
        Index(
            "ix_institutions_domains",
            "domains",
            postgresql_using="gin",
            postgresql_ops={"domains": "jsonb_path_ops"},
        ),
        Index("ix_institutions_search_vector", "search_vector", postgresql_using="gin"),
    )
