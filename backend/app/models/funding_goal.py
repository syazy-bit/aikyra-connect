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
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundingGoalStatus(str, enum.Enum):
    """Stored lifecycle of a verified funding goal.

    Only OPEN and CLOSED are persisted. The public "FULLY_FUNDED" state is
    derived by the service from the money math (raised >= goal), never stored,
    so the stored lifecycle can never drift from the contribution totals.
    """

    OPEN = "open"
    CLOSED = "closed"


class FundingGoal(Base):
    """A project's verified community-funding goal.

    1:1 with a project (project_id is UNIQUE) — an approved solution has at
    most one verified funding goal, mirroring the project_report singleton.

    All money is stored as integer minor units (paise) in BIGINT columns so
    the server can aggregate fundraising exactly. There is no floating-point
    money anywhere in the system.
    """

    __tablename__ = "funding_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    goal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )
    status: Mapped[FundingGoalStatus] = mapped_column(
        Enum(
            FundingGoalStatus,
            name="funding_goal_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=FundingGoalStatus.OPEN,
        server_default=FundingGoalStatus.OPEN.value,
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
        UniqueConstraint("project_id", name="uq_funding_goals_project"),
        Index("ix_funding_goals_status", "status"),
        CheckConstraint("goal_minor > 0", name="ck_funding_goals_goal_positive"),
        CheckConstraint(
            "currency = 'INR'", name="ck_funding_goals_currency_inr"
        ),
    )