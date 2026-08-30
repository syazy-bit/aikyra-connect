"""Development-only DEMO funding cleanup (hackathon demo).

Removes ONLY the COMPLETED contribution rows created by
scripts/seed_demo_funding.py for the selected demo project's funding goal.

It deliberately NEVER touches:
    - normal (non-demo) user contributions
    - funding goals
    - projects
    - users
    - any other funding/team/institution data

Idempotent: safe to run repeatedly. Running it when nothing was seeded simply
reports 0 removed.

Project selection mirrors the seed script (priority):
    1. `--project-id <uuid>`
    2. `DEMO_FUNDING_PROJECT_ID` environment variable
    3. the most recently approved project

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.clear_demo_funding
    .venv\\Scripts\\python.exe -m scripts.clear_demo_funding --project-id <uuid>
"""

import argparse
import os
import uuid

from app.core.database import SessionLocal
from app.models.funding_contribution import FundingContribution
from app.repositories.funding_repository import FundingRepository
from app.repositories.project_repository import ProjectRepository

from scripts.seed_demo_funding import (
    DEMO_SPLITS_MINOR,
    _demo_contribution_id,
)


def _select_project_id(db) -> tuple[uuid.UUID | None, str]:
    explicit = os.getenv("DEMO_FUNDING_PROJECT_ID")
    if explicit:
        try:
            project = ProjectRepository(db).get_by_id(uuid.UUID(explicit))
        except (ValueError, TypeError):
            project = None
        if project is not None:
            return project.id, f"explicit DEMO_FUNDING_PROJECT_ID ({explicit})"
        return None, f"DEMO_FUNDING_PROJECT_ID={explicit} (not found)"

    projects, _ = ProjectRepository(db).list_projects(skip=0, limit=1)
    if projects:
        return projects[0].id, "most recently approved project"
    return None, "no approved project available"


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear AIKYRA demo funding (dev only).")
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Explicit project UUID whose demo contributions to remove.",
    )
    args = parser.parse_args()
    if args.project_id:
        os.environ["DEMO_FUNDING_PROJECT_ID"] = args.project_id

    db = SessionLocal()
    try:
        project_id, how = _select_project_id(db)
        if project_id is None:
            print("=" * 64)
            print("Demo funding cleanup: no project to target.")
            print("Pass --project-id <uuid> to choose one.")
            print("=" * 64)
            return

        goal = FundingRepository(db).get_goal_by_project(project_id)
        if goal is None:
            print("=" * 64)
            print("Demo funding cleanup: project has no funding goal.")
            print("Nothing to remove; no goal, project or users were touched.")
            print("=" * 64)
            return

        demo_ids = [
            _demo_contribution_id(goal.id, index)
            for index in range(len(DEMO_SPLITS_MINOR))
        ]
        rows = db.query(FundingContribution).filter(
            FundingContribution.id.in_(demo_ids)
        )
        total = rows.count()
        removed = 0
        for row in list(rows.all()):
            db.delete(row)
            db.flush()
            removed += 1
        db.commit()

        print("=" * 64)
        print("DEMO funding cleanup complete (development only).")
        print(f"  project  : {project_id}")
        print(f"  selected : {how}")
        print(f"  removed  : {removed} demo contribution row(s)")
        if removed:
            print("  note     : goal, projects and users were NOT touched.")
        print("=" * 64)
    finally:
        db.close()


if __name__ == "__main__":
    main()
