import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DnaValidationStatus(str, enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"


class DnaSource(str, enum.Enum):
    DETERMINISTIC_BASELINE = "deterministic_baseline"
    AI_MODEL = "ai_model"
    HUMAN = "human"


class UrgencyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemDna(Base):
    """Structured understanding of a challenge.

    Everything here is system-derived or human-refined — never citizen input.
    AI/deterministic output is advisory (pending_validation) until a human
    validates it.
    """

    __tablename__ = "problem_dna"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    primary_domain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_domains: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    subdomain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    problem_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geographic_context: Mapped[str | None] = mapped_column(String(50), nullable=True)
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UrgencyLevel.MEDIUM,
        server_default=UrgencyLevel.MEDIUM.value,
    )
    affected_stakeholders: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_expertise: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    potential_solution_areas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    signals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_by: Mapped[DnaSource] = mapped_column(
        Enum(DnaSource, name="dna_source",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=DnaSource.DETERMINISTIC_BASELINE,
        server_default=DnaSource.DETERMINISTIC_BASELINE.value,
    )
    analyzer_version: Mapped[str] = mapped_column(String(50), nullable=False)
    validation_status: Mapped[DnaValidationStatus] = mapped_column(
        Enum(DnaValidationStatus, name="dna_validation_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=DnaValidationStatus.PENDING_VALIDATION,
        server_default=DnaValidationStatus.PENDING_VALIDATION.value,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_problem_dna_primary_domain", "primary_domain"),)
