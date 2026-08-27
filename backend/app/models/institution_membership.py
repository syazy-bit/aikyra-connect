import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InstitutionMembershipRole(str, enum.Enum):
    OWNER = "owner"
    REPRESENTATIVE = "representative"
    REVIEWER = "reviewer"
    FACULTY = "faculty"
    STUDENT = "student"


class InstitutionMembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class InstitutionMembership(Base):
    """Join table linking users to institutions with a role and status.

    Authorization is resolved from this table at request time — never from
    JWT claims or client-supplied fields.
    """

    __tablename__ = "institution_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[InstitutionMembershipRole] = mapped_column(
        String(20), nullable=False,
    )
    status: Mapped[InstitutionMembershipStatus] = mapped_column(
        String(20), nullable=False, default=InstitutionMembershipStatus.ACTIVE,
        server_default=InstitutionMembershipStatus.ACTIVE.value,
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
        UniqueConstraint("user_id", "institution_id", name="uq_membership_user_institution"),
        Index("ix_membership_institution", "institution_id"),
        Index("ix_membership_user", "user_id"),
    )
