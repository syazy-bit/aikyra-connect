# Register models on Base.metadata for Alembic autogenerate and test schema creation.
import app.models.user  # noqa: F401
import app.models.institution_membership  # noqa: F401
import app.models.team  # noqa: F401
import app.models.project  # noqa: F401
import app.models.organization  # noqa: F401
import app.models.support_offer  # noqa: F401
import app.models.project_impact_metric  # noqa: F401
import app.models.project_report  # noqa: F401
import app.models.funding_goal  # noqa: F401
import app.models.funding_contribution  # noqa: F401
import app.models.challenge_review_audit  # noqa: F401
