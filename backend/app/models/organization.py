import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text as sa_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_NORMALIZED_NAME_EXPRESSION = (
    "lower(btrim(regexp_replace(regexp_replace(name, '[^a-zA-Z0-9]+', ' ', 'g'), "
    "'\\s+', ' ', 'g')))"
)


class Organization(Base):
    """An industry or NGO organization that can support approved solutions.

    Deliberately minimal for the MVP: no verification workflow, no capability
    profile, and a single DB-backed manager (`manager_user_id`) who is set
    server-side on registration. Support offers derive the offering
    organization from this manager relationship — never from the client — so
    a user cannot pose as an organization they do not manage.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_user_id: Mapped[uuid.UUID] = mapped_column(
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
        Index(
            "uq_organizations_name_normalized",
            sa_text(_NORMALIZED_NAME_EXPRESSION),
            unique=True,
        ),
        Index("ix_organizations_manager", "manager_user_id"),
    )
