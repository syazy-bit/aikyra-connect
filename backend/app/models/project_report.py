import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectReport(Base):
    """The final outcome report for an implemented project (CP8).

    A single, lead-authored report per project (1:1 — project_id is UNIQUE)
    that tells the conclusive story of an approved solution: what was
    delivered, the results, lessons learned and next steps. Publicly readable
    like impact metrics and support offers; only the active team lead may
    create/edit/delete it, and only once the project is `implemented`.

    project_id is always server-resolved from the URL path — never accepted
    from the client. The report has no standalone ID route: it is identified
    by its project, so cross-project access is structurally impossible.
    """

    __tablename__ = "project_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    results: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        UniqueConstraint("project_id", name="uq_project_reports_project"),
    )