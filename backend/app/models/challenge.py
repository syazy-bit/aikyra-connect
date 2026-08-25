import enum
import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_SEARCH_VECTOR_EXPRESSION = (
    "to_tsvector('english', coalesce(title, '') || ' ' || "
    "coalesce(description, '') || ' ' || coalesce(location, ''))"
)


class ChallengeStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    REJECTED = "rejected"


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ChallengeStatus] = mapped_column(
        Enum(
            ChallengeStatus,
            name="challenge_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ChallengeStatus.SUBMITTED,
        server_default=ChallengeStatus.SUBMITTED.value,
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
    # Database-generated full-text search vector (Phase 3 discovery).
    # Maintained entirely by PostgreSQL; never written by application code.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(_SEARCH_VECTOR_EXPRESSION, persisted=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_challenges_status", "status"),
        Index("ix_challenges_created_at", "created_at"),
        Index("ix_challenges_search_vector", "search_vector", postgresql_using="gin"),
    )
