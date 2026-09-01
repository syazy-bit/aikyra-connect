import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.challenge import ChallengeStatus
from app.models.problem_dna import DnaValidationStatus


class ChallengeReviewAudit(Base):
    """Audit log for challenge review actions.

    Records status transitions and DNA validation actions performed by
    platform reviewers with admin capabilities.
    """

    __tablename__ = "challenge_review_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_status: Mapped[ChallengeStatus | None] = mapped_column(
        Enum(
            ChallengeStatus,
            name="challenge_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    new_status: Mapped[ChallengeStatus | None] = mapped_column(
        Enum(
            ChallengeStatus,
            name="challenge_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    previous_dna_validation_status: Mapped[DnaValidationStatus | None] = mapped_column(
        Enum(
            DnaValidationStatus,
            name="dna_validation_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    new_dna_validation_status: Mapped[DnaValidationStatus | None] = mapped_column(
        Enum(
            DnaValidationStatus,
            name="dna_validation_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_challenge_review_audit_challenge", "challenge_id"),
        Index("ix_challenge_review_audit_reviewer", "reviewer_id"),
    )