import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundingContributionStatus(str, enum.Enum):
    """State machine of one funding contribution.

    Only COMPLETED contributions count towards the public raised total;
    PENDING, FAILED and REFUNDED money is never counted. A later payment
    slice drives these transitions; this slice records them server-side.
    """

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class FundingContribution(Base):
    """A single contribution towards a project's verified funding goal.

    Contributed amounts are integer minor units (paise). The supporter's
    account is recorded privately (contributed_by) so the platform can later
    offer authenticated, opt-in supporter surfaces; it is never exposed by the
    public funding summary, which only reports an aggregate supporter count.
    """

    __tablename__ = "funding_contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("funding_goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    contributed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[FundingContributionStatus] = mapped_column(
        Enum(
            FundingContributionStatus,
            name="funding_contribution_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=FundingContributionStatus.PENDING,
        server_default=FundingContributionStatus.PENDING.value,
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

    __table_args__ = (
        Index("ix_funding_contributions_goal", "goal_id"),
        Index("ix_funding_contributions_status", "status"),
        CheckConstraint(
            "amount_minor > 0", name="ck_funding_contributions_amount_positive"
        ),
    )