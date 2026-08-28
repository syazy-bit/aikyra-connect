import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamStatus(str, enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class TeamRole(str, enum.Enum):
    LEAD = "lead"
    MEMBER = "member"


class TeamMembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class Team(Base):
    """Team representing a group of users from an institution working on a challenge."""

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[TeamStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TeamStatus.FORMING,
        server_default=TeamStatus.FORMING.value,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
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
        UniqueConstraint(
            "institution_id", "challenge_id", "name", name="uq_team_inst_challenge_name"
        ),
        Index("ix_teams_institution", "institution_id"),
        Index("ix_teams_challenge", "challenge_id"),
        Index("ix_teams_created_by", "created_by"),
    )


class TeamMembership(Base):
    """Join table linking users to teams with a role and status."""

    __tablename__ = "team_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[TeamRole] = mapped_column(
        String(20), nullable=False,
    )
    status: Mapped[TeamMembershipStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TeamMembershipStatus.ACTIVE,
        server_default=TeamMembershipStatus.ACTIVE.value,
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
        UniqueConstraint("team_id", "user_id", name="uq_team_membership_user"),
        Index("ix_team_memberships_team", "team_id"),
        Index("ix_team_memberships_user", "user_id"),
        Index("ix_team_memberships_invited_by", "invited_by"),
    )