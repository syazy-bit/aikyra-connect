"""Development-only demo seed — CP8 project outcome report.

Writes the demo outcome report for the CP7 demo project. The report is the
conclusive final story of an *implemented* approved solution and deliberately
mirrors the CP7 demo impact metrics (120 households reached, 4 villages
covered, 85 pilot participants) so the "impact evidence -> outcome report"
story is coherent in the demo.

Rules:
1. A report can only exist once the project is 'implemented'. If no project is
   implemented yet, the script prints guidance and exits cleanly — it never
   advances the lifecycle (that is CP6's job, never a seed script's).
2. A report is a 1:1 project singleton. If the demo project already has a
   report, it is preserved untouched — never overwritten, never duplicated.
2. Existing reports on other projects are never touched.

Idempotent: safe to run repeatedly. Existing reports are preserved; the only
thing a rerun does is report 'already present'. Never referenced by Alembic;
never executed by application startup.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_cp8_demo
"""

from app.core.database import SessionLocal
from app.models.project import ProjectStatus
from app.repositories.project_report_repository import ProjectReportRepository
from app.repositories.project_repository import ProjectRepository

REPORT = {
    "summary": (
        "The pilot delivered clean-energy access to four rural villages: "
        "120 households reached, 85 community participants trained, and a "
        "full handover to local operators."
    ),
    "results": (
        "120 households connected to clean energy; 4 villages covered across "
        "the pilot rollout; 85 students and community members trained to "
        "operate and maintain the deployments."
    ),
    "lessons_learned": (
        "Community buy-in at the village level drives adoption far more than "
        "equipment choice, and training local operators early makes the "
        "handover sustainable."
    ),
    "next_steps": (
        "Scale the model to two additional districts and publish a longer-"
        "term follow-up on energy usage and household savings."
    ),
}


def _find_implemented_demo_project(db):
    """Return the most recently created demo project if it is implemented.

    Projects are materialized only by the accept -> project hook; the seed
    never materializes or advances them. We look for any project already at
    the terminal 'implemented' stage.
    """
    projects, _ = ProjectRepository(db).list_projects(
        status=ProjectStatus.IMPLEMENTED, skip=0, limit=1
    )
    return projects[0] if projects else None


def _ensure_report(db, project):
    """Ensures exactly one outcome report on the demo project.

    Idempotent: if a report already exists it is returned untouched
    (report_created=False). Flushes but does not commit.
    """
    repo = ProjectReportRepository(db)
    existing = repo.get_by_project(project.id)
    if existing is not None:
        return existing, False
    report = repo.create(
        {
            "project_id": project.id,
            "summary": REPORT["summary"],
            "results": REPORT["results"],
            "lessons_learned": REPORT["lessons_learned"],
            "next_steps": REPORT["next_steps"],
        }
    )
    return report, True


def main() -> None:
    db = SessionLocal()
    try:
        project = _find_implemented_demo_project(db)
        if project is None:
            print("=" * 64)
            print("CP8 demo seed: no implemented project found.")
            print("The outcome report can only be written once a project is")
            print("implemented. Advance a project to 'implemented' first, then")
            print("rerun seed_cp8_demo.")
            print("=" * 64)
            return

        report, report_created = _ensure_report(db, project)
        db.commit()

        print("=" * 64)
        print("CP8 demo seed complete.")
        print(f"  project      : {project.title[:60]} (implemented)")
        print(
            f"  report       : "
            f"{'created' if report_created else 'already present (preserved)'}"
        )
        print()
        print("Public report link:")
        print(f"  GET /api/projects/{project.id}/report")
        print("=" * 64)
    finally:
        db.close()


if __name__ == "__main__":
    main()