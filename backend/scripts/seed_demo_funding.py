"""Development-only DEMO seed — verified community funding (hackathon demo).

Prepares ONE presentation-ready approved project to open at:

    GOAL:   ₹50,000   (goal_minor = 5_000_000)
    RAISED: ₹15,000   (raised_minor = 1_500_000)
    PROGRESS: 30%     (progress_bp = 3000, derived server-side)

No fake numbers are injected into the API or the FundingService. The demo
figures exist as real `funding_contributions` rows (stored COMPLETED) on the
project's real verified `funding_goals` row, so they are aggregated by the
normal DB-authoritative pipeline exactly like a real contribution.

Idempotency & cleanup (deterministic marker):
    The demo contributions are created with deterministic UUIDs derived from
    a fixed namespace + the goal id. Re-running the seed detects those exact
    rows and does nothing, so running it twice can never double the raised
    total. `scripts/clear_demo_funding.py` removes ONLY those deterministic
    rows — it never touches normal contributions, goals, projects or users.

Selecting the project (priority):
    1. `--project-id <uuid>`      explicit choice (safest for a presentation)
    2. `DEMO_FUNDING_PROJECT_ID`  environment variable
    3. the most recently approved project (deterministic default)

Rules:
    - Never referenced by Alembic; never executed at application startup.
    - Prefers existing DB users (the project team's members) as contributors.
      Only falls back to creating a demo supporter user if no user exists at
      all (which would otherwise make a contribution impossible by schema).
    - Never deletes or alters unrelated funding/goal/user data.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_demo_funding
    .venv\\Scripts\\python.exe -m scripts.seed_demo_funding --project-id <uuid>
"""

import argparse
import os
import sys
import uuid

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.funding_contribution import (
    FundingContribution,
    FundingContributionStatus,
)
from app.models.funding_goal import FundingGoal, FundingGoalStatus
from app.models.project import Project
from app.models.team import TeamMembershipStatus
from app.models.user import User
from app.repositories.funding_repository import FundingRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.team_repository import TeamMembershipRepository

DEMO_GOAL_MINOR = 5_000_000      # ₹50,000
DEMO_RAISED_MINOR = 1_500_000    # ₹15,000  (total of the demo splits below)

# Individual completed demo contributions that sum to DEMO_RAISED_MINOR.
# Expressed in minor units (paise): ₹5,000 / ₹4,000 / ₹3,000 / ₹2,000 / ₹1,000.
DEMO_SPLITS_MINOR = [500_000, 400_000, 300_000, 200_000, 100_000]

# Fixed namespace so demo contribution ids are deterministic and reusable by
# the cleanup script. Never collide with ids from the application's random
# uuid4 generator for practical purposes.
DEMO_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c9")


def _demo_contribution_id(goal_id: uuid.UUID, index: int) -> uuid.UUID:
    """Deterministic uuid for the demo contribution at `index` on `goal_id`."""
    return uuid.uuid5(DEMO_NAMESPACE, f"{goal_id}:demo:{index}")


def _select_project(db) -> tuple[Project | None, str]:
    """Choose the demo project by explicit id, env var, or newest approved."""
    repo = ProjectRepository(db)
    explicit = os.getenv("DEMO_FUNDING_PROJECT_ID")
    if explicit:
        try:
            project = repo.get_by_id(uuid.UUID(explicit))
        except (ValueError, TypeError):
            project = None
        if project is not None:
            return project, f"explicit DEMO_FUNDING_PROJECT_ID ({explicit})"
        return None, f"DEMO_FUNDING_PROJECT_ID={explicit} (not found)"

    projects, _ = repo.list_projects(skip=0, limit=1)
    if projects:
        return projects[0], "most recently approved project"
    return None, "no approved project available"


def _ensure_goal(db, project_id: uuid.UUID) -> FundingGoal:
    """Return the project's funding goal, setting it to ₹50,000 if needed."""
    goal = FundingRepository(db).get_goal_by_project(project_id)
    if goal is None:
        goal = FundingGoal(
            id=uuid.uuid4(),
            project_id=project_id,
            goal_minor=DEMO_GOAL_MINOR,
            currency="INR",
            status=FundingGoalStatus.OPEN,
        )
        db.add(goal)
        db.flush()
        return goal
    # Reuse the existing goal but pin the target to the presentation value.
    if goal.goal_minor != DEMO_GOAL_MINOR:
        goal.goal_minor = DEMO_GOAL_MINOR
    if goal.status != FundingGoalStatus.OPEN:
        goal.status = FundingGoalStatus.OPEN
    db.flush()
    return goal


def _supporter_ids(db, project: Project) -> list[uuid.UUID]:
    """Distinct existing users to act as demo supporters.

    Prefer the project team's ACTIVE members (real, project-relevant users).
    Fall back to any platform user, and finally to a freshly created demo
    supporter only if no user exists at all.
    """
    membership_repo = TeamMembershipRepository(db)
    members = membership_repo.get_memberships_for_team(
        project.team_id, status=TeamMembershipStatus.ACTIVE
    )
    ids = [m.user_id for m in members]
    if ids:
        # Deduplicate while preserving order.
        return list(dict.fromkeys(ids))

    user_ids = list(db.execute(select(User.id)).scalars())
    if user_ids:
        return user_ids

    raise RuntimeError(
        "No user exists to own the demo contribution. Create a user/team "
        "first, then rerun this seed."
    )


def _seed_contributions(db, goal_id: uuid.UUID, supporter_ids: list[uuid.UUID]) -> int:
    """Insert the deterministic COMPLETED demo contribution rows.

    Returns the number of rows created (0 when all already exist). Existing
    rows with the deterministic ids are left untouched.
    """
    created = 0
    for index, amount in enumerate(DEMO_SPLITS_MINOR):
        contribution_id = _demo_contribution_id(goal_id, index)
        existing = db.get(FundingContribution, contribution_id)
        if existing is not None:
            continue
        supported_by = supporter_ids[index % len(supporter_ids)]
        db.add(
            FundingContribution(
                id=contribution_id,
                goal_id=goal_id,
                contributed_by=supported_by,
                amount_minor=amount,
                status=FundingContributionStatus.COMPLETED,
            )
        )
        created += 1
    db.flush()
    return created


def main() -> None:
    # Make the ₹ symbol printable on Windows (cp1252) consoles.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Seed AIKYRA demo funding (dev only).")
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Explicit project UUID to seed (safer for a presentation).",
    )
    args = parser.parse_args()
    if args.project_id:
        os.environ["DEMO_FUNDING_PROJECT_ID"] = args.project_id

    db = SessionLocal()
    try:
        project, how = _select_project(db)
        if project is None:
            print("=" * 64)
            print("Demo funding seed: no approved project to seed.")
            print("Seed a project first, or pass --project-id <uuid>.")
            print("=" * 64)
            return

        goal = _ensure_goal(db, project.id)
        supporter_ids = _supporter_ids(db, project)
        created = _seed_contributions(db, goal.id, supporter_ids)
        db.commit()

        # Real DB-authoritative aggregate after the insert (same pipeline the
        # public API uses).
        raised, supporters = FundingRepository(db).aggregate_contributions(goal.id)
        progress_bp = (
            0
            if goal.goal_minor <= 0
            else min(10000, raised * 10000 // goal.goal_minor)
        )

        print("=" * 64)
        print("DEMO funding seed complete (development only).")
        print(f"  project    : {project.title[:60]}")
        print(f"  selected   : {how}")
        print(f"  goal_minor : {goal.goal_minor}  (₹{goal.goal_minor / 100:,.2f})")
        print(f"  raised     : {raised}  (₹{raised / 100:,.2f})")
        print(f"  supporters : {supporters}")
        print(f"  progress_bp: {progress_bp}")
        print(
            f"  demo rows  : {created} created, "
            f"{len(DEMO_SPLITS_MINOR) - created} already present"
        )
        print()
        print("Public funding endpoint:")
        print(f"  GET /api/projects/{project.id}/funding")
        print("=" * 64)
    finally:
        db.close()


if __name__ == "__main__":
    main()
