import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupportType(str, enum.Enum):
    FUNDING = "funding"
    EQUIPMENT = "equipment"
    MENTORSHIP = "mentorship"
    PILOT_SUPPORT = "pilot_support"


class SupportOfferStatus(str, enum.Enum):
    """Lifecycle of a support offer. The MVP only reaches 'offered'; a later
    slice may introduce accept/decline transitions. Stored server-side."""

    OFFERED = "offered"


class SupportOffer(Base):
    """An offer of support from an organization to an approved project.

    organization_id and offered_by are always server-resolved from the
    authenticated organization manager — never trusted from the client.
    """

    __tablename__ = "support_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    offered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    support_type: Mapped[SupportType] = mapped_column(
        Enum(
            SupportType,
            name="support_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SupportOfferStatus] = mapped_column(
        Enum(
            SupportOfferStatus,
            name="support_offer_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SupportOfferStatus.OFFERED,
        server_default=SupportOfferStatus.OFFERED.value,
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
        Index("ix_support_offers_project", "project_id"),
        Index("ix_support_offers_organization", "organization_id"),
    )
