from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.funding_goal import FundingGoal, FundingGoalStatus
from app.repositories.funding_repository import FundingRepository
from app.repositories.project_repository import ProjectRepository


# Public display statuses. Only OPEN/CLOSED are stored on the goal; FULLY_FUNDED
# is derived by this service from the money math (raised >= goal) so it can
# never drift from the contribution totals.
FUNDING_STATUS_OPEN = "OPEN"
FUNDING_STATUS_FULLY_FUNDED = "FULLY_FUNDED"
FUNDING_STATUS_CLOSED = "CLOSED"

# 1 INR = 100 paise; minor units are the only money representation in the app.
MINOR_UNITS_PER_CURRENCY_UNIT = 100


class FundingService:
    """Derives every fundraising number from COMPLETED contributions.

    The database is authoritative. raised_minor is the sum of completed
    contributions; supporter_count is the count of distinct supporters with at
    least one completed contribution; every remaining value (remaining_minor,
    progress_bp, display status) is computed here with integer arithmetic —
    never floats, never client-supplied. No individual contribution, supporter
    account or amount is ever returned publicly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.funding_repository = FundingRepository(db)
        self.project_repository = ProjectRepository(db)

    def get_public_funding(self, project_id: UUID) -> dict | None:
        """Server-derived funding summary for one approved solution.

        Returns a summary dict, or None when the project has no verified
        funding goal (a safe empty response, never fabricated zeros).
        """
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        goal = self.funding_repository.get_goal_by_project(project_id)
        if goal is None:
            return None
        raised_minor, supporter_count = self.funding_repository.aggregate_contributions(
            goal.id
        )
        return self._summary(project_id, goal, raised_minor, supporter_count)

    def get_public_funding_for_projects(
        self, project_ids: list[UUID]
    ) -> dict[UUID, dict]:
        """Batch funding summaries keyed by project_id (used by list endpoints).

        Runs two grouped queries total instead of an N+1 per project.
        """
        ids = [pid for pid in project_ids if pid is not None]
        if not ids:
            return {}
        goals = self.funding_repository.list_goals_for_projects(ids)
        if not goals:
            return {}
        aggregates = self.funding_repository.aggregate_for_goals([g.id for g in goals])
        return {
            self._as_uuid(goal.project_id): self._summary(
                self._as_uuid(goal.project_id),
                goal,
                *(aggregates.get(goal.id, (0, 0))),
            )
            for goal in goals
        }

    # --- Owner management (authorization + commit live in ProjectService) -----

    def get_goal(self, project_id: UUID) -> FundingGoal | None:
        """The project's stored funding goal, or None when none exists."""
        return self.funding_repository.get_goal_by_project(project_id)

    def create_goal(
        self, project_id: UUID, goal_minor: int, currency: str = "INR"
    ) -> FundingGoal:
        """Create the project's funding goal (1:1 singleton).

        Flush-of-record write only — the caller owns the transaction and maps
        any IntegrityError (e.g. the UNIQUE-project race guard) to a 409. A
        second goal for the same project is rejected up front for a clean,
        common-path ConflictError before any row is touched.
        """
        if self.funding_repository.get_goal_by_project(project_id) is not None:
            raise ConflictError("This project already has a funding goal.")
        return self.funding_repository.create_goal(
            {
                "project_id": project_id,
                "goal_minor": goal_minor,
                "currency": currency,
                "status": FundingGoalStatus.OPEN,
            }
        )

    def update_goal(self, project_id: UUID, goal_minor: int) -> FundingGoal:
        """Edit an OPEN goal's amount, never the money already raised.

        Only an OPEN goal is editable. Lowering the target below the total of
        completed contributions is rejected (409): the derived FULLY_FUNDED
        status must stay a true reflection of real money, never a re-labelled
        target, and an owner must not be able to retroactively re-draw a goal
        under what supporters have already given. Raised money is recomputed
        from the contribution table after every change — it is never editable.
        """
        goal = self.funding_repository.get_goal_by_project(project_id)
        if goal is None:
            raise NotFoundError("FundingGoal", project_id)
        if goal.status != FundingGoalStatus.OPEN:
            raise ConflictError(
                "A closed funding goal cannot be edited."
            )
        raised_minor, _ = self.funding_repository.aggregate_contributions(goal.id)
        if goal_minor < raised_minor:
            raise ConflictError(
                "The funding goal cannot be lowered below the amount already raised."
            )
        self.funding_repository.update_goal(goal, {"goal_minor": goal_minor})
        return goal

    def close_goal(self, project_id: UUID) -> FundingGoal:
        """Close an OPEN goal (terminal lifecycle state).

        Close only flips the stored lifecycle status to CLOSED. Historical
        contribution rows and their totals are preserved; totals are never
        reset and no "fully funded" state is fabricated. CLOSED takes display
        precedence over the derived FULLY_FUNDED in the summary.
        """
        goal = self.funding_repository.get_goal_by_project(project_id)
        if goal is None:
            raise NotFoundError("FundingGoal", project_id)
        if goal.status == FundingGoalStatus.CLOSED:
            raise ConflictError("This funding goal is already closed.")
        self.funding_repository.update_goal(
            goal, {"status": FundingGoalStatus.CLOSED}
        )
        return goal

    @staticmethod
    def _as_uuid(value: UUID | str) -> UUID:
        """Normalize a stored project_id (UUID or string) to a UUID object.

        The database column is a UUID type, but a value can briefly live in
        the session identity map as the string it was set with; keying batch
        funding summaries by a normalized UUID guarantees list lookups match
        whatever form the caller holds.
        """
        return value if isinstance(value, UUID) else UUID(str(value))

    def _summary(
        self,
        project_id: UUID,
        goal: FundingGoal,
        raised_minor: int,
        supporter_count: int,
    ) -> dict:
        goal_minor = int(goal.goal_minor)
        raised_minor = int(raised_minor)
        supporter_count = int(supporter_count)

        if goal.status == FundingGoalStatus.CLOSED:
            display_status = FUNDING_STATUS_CLOSED
        elif raised_minor >= goal_minor:
            display_status = FUNDING_STATUS_FULLY_FUNDED
        else:
            display_status = FUNDING_STATUS_OPEN

        # Integer-only percentage: basis points (0..10000), capped at 10000 so
        # an over-funded goal never degrades the progress bar.
        if goal_minor <= 0:
            progress_bp = 0
        else:
            progress_bp = min(10000, (raised_minor * 10000) // goal_minor)

        remaining_minor = max(goal_minor - raised_minor, 0)

        return {
            "project_id": project_id,
            "goal_minor": goal_minor,
            "raised_minor": raised_minor,
            "remaining_minor": remaining_minor,
            "currency": goal.currency,
            "progress_bp": progress_bp,
            "supporter_count": supporter_count,
            "status": display_status,
        }