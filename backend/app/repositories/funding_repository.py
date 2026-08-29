from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.funding_contribution import (
    FundingContribution,
    FundingContributionStatus,
)
from app.models.funding_goal import FundingGoal


class FundingRepository:
    """Database access for verified funding goals and contributions.

    Read-only aggregations plus flush-only writes — transactions are owned by
    the service layer. All money math is integer arithmetic in minor units
    performed by the database; the API never receives pre-totaled values from
    a client.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Goals -------------------------------------------------------------

    def get_goal_by_project(self, project_id: UUID) -> FundingGoal | None:
        return self.db.execute(
            select(FundingGoal).where(FundingGoal.project_id == project_id)
        ).scalar_one_or_none()

    def get_goal(self, goal_id: UUID) -> FundingGoal | None:
        return self.db.get(FundingGoal, goal_id)

    def list_goals_for_projects(self, project_ids: list[UUID]) -> list[FundingGoal]:
        if not project_ids:
            return []
        return list(
            self.db.execute(
                select(FundingGoal).where(FundingGoal.project_id.in_(project_ids))
            ).scalars()
        )

    def create_goal(self, data: dict) -> FundingGoal:
        goal = FundingGoal(**data)
        self.db.add(goal)
        self.db.flush()
        return goal

    def update_goal(self, goal: FundingGoal, data: dict) -> FundingGoal:
        for key, value in data.items():
            setattr(goal, key, value)
        self.db.flush()
        return goal

    def delete_goal(self, goal: FundingGoal) -> None:
        self.db.delete(goal)
        self.db.flush()

    # --- Contributions -----------------------------------------------------

    def create_contribution(self, data: dict) -> FundingContribution:
        contribution = FundingContribution(**data)
        self.db.add(contribution)
        self.db.flush()
        return contribution

    def aggregate_contributions(self, goal_id: UUID) -> tuple[int, int]:
        """(raised_minor, supporter_count) for one goal.

        Only COMPLETED contributions count: PENDING/FAILED/REFUNDED money is
        never summed. supporter_count is the number of distinct supporters
        with at least one completed contribution.
        """
        row = self.db.execute(
            select(
                func.coalesce(func.sum(FundingContribution.amount_minor), 0),
                func.count(distinct(FundingContribution.contributed_by)),
            ).where(
                FundingContribution.goal_id == goal_id,
                FundingContribution.status == FundingContributionStatus.COMPLETED,
            )
        ).one()
        return int(row[0]), int(row[1])

    def aggregate_for_goals(
        self, goal_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int]]:
        """(raised_minor, supporter_count) per goal_id in one grouped query."""
        if not goal_ids:
            return {}
        rows = self.db.execute(
            select(
                FundingContribution.goal_id,
                func.coalesce(func.sum(FundingContribution.amount_minor), 0),
                func.count(distinct(FundingContribution.contributed_by)),
            )
            .where(
                FundingContribution.goal_id.in_(goal_ids),
                FundingContribution.status == FundingContributionStatus.COMPLETED,
            )
            .group_by(FundingContribution.goal_id)
        ).all()
        return {row[0]: (int(row[1]), int(row[2])) for row in rows}