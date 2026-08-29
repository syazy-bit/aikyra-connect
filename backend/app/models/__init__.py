# Register models on Base.metadata for Alembic autogenerate and test schema creation.
import app.models.user  # noqa: F401
import app.models.institution_membership  # noqa: F401
import app.models.team  # noqa: F401
import app.models.project  # noqa: F401
import app.models.organization  # noqa: F401
import app.models.support_offer  # noqa: F401
