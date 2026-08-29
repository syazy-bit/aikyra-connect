"""Development-only demo seed — industry/NGO support + project impact.

Ensures the complete Phase 6/7 demo scenario (industry/NGO support and project
impact) exists on top of the existing Phase 4 seeds without touching
university-side data:

1. Ensures a demo industry user (`partner@aikyra.dev`) exists. The account has
   NO institution membership — industry partners are not university members and
   the approved-solutions surface is public.
2. Ensures exactly one organization managed by that user (so `POST
   /api/projects/{id}/offers` works for the demo login).
3. Finds the first demo project (materialized by the accept → project hook)
   and ensures exactly one support offer (SolarNova Foundation · mentorship)
   on it, so the "Approved Solutions → project → offer" story can be shown
   immediately from both the university and industry sides.
4. Ensures the demo project's impact metrics exist (Households reached /
   Villages covered / Pilot participants) so the "Impact" section of the
   public project page opens populated.

Deliberately does NOT create projects: project materialization belongs to the
proposal accept hook, never to a seed script. If no project exists yet, the
script prints a warning and exits cleanly.

Idempotent: safe to run repeatedly. Users, organizations, offers and impact
metrics are reused if they already exist; no duplicates are ever created.
Existing metrics are preserved. Never referenced by Alembic; never executed by
application startup.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_cp5_demo
"""

from app.core.database import SessionLocal
from app.models.project import ProjectStatus
from app.models.support_offer import SupportOfferStatus, SupportType
from app.repositories.impact_metric_repository import ImpactMetricRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.support_offer_repository import SupportOfferRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import pwd_context

PARTNER_USER = {
    "email": "partner@aikyra.dev",
    "password": "partner123",
    "full_name": "Demo Industry Partner",
    "is_platform_reviewer": False,
}

ORGANIZATION = {
    "name": "SolarNova Foundation",
    "description": "Industry demo organization for approved-solution support.",
}

OFFER = {
    "support_type": SupportType.MENTORSHIP,
    "message": "Happy to mentor the pilot and provide technical guidance.",
}

IMPACT_METRICS = [
    {
        "name": "Households reached",
        "value": "120",
        "unit": "households",
        "description": "Households benefiting from the pilot deployment.",
    },
    {
        "name": "Villages covered",
        "value": "4",
        "unit": "villages",
        "description": "Villages included in the pilot rollout.",
    },
    {
        "name": "Pilot participants",
        "value": "85",
        "unit": "people",
        "description": "Students and community members participating in the pilot.",
    },
]


def _ensure_partner_user(db):
    """Return the partner user. Flushes but does not commit."""
    repo = UserRepository(db)
    user = repo.get_by_email(PARTNER_USER["email"])
    if user is not None:
        if user.is_platform_reviewer != PARTNER_USER["is_platform_reviewer"]:
            user.is_platform_reviewer = PARTNER_USER["is_platform_reviewer"]
            db.flush()
        return user, False
    user = repo.create(
        {
            "email": PARTNER_USER["email"],
            "hashed_password": pwd_context.hash(PARTNER_USER["password"]),
            "full_name": PARTNER_USER["full_name"],
            "is_platform_reviewer": PARTNER_USER["is_platform_reviewer"],
        }
    )
    return user, True


def _ensure_organization(db, partner):
    """Return the partner organization. Flushes but does not commit."""
    repo = OrganizationRepository(db)
    organization = repo.get_by_manager(partner.id)
    if organization is not None:
        return organization, False
    organization = repo.create(
        {
            "name": ORGANIZATION["name"],
            "description": ORGANIZATION["description"],
            "manager_user_id": partner.id,
        }
    )
    return organization, True


def _find_first_active_project(db):
    """Return the most recently created demo project, or None.

    Projects are materialized only by the accept -> project hook, and their
    lifecycle can be anything (prototype -> pilot -> implemented), so the
    lookup walks those statuses from earliest stage onward.
    """
    for status in (ProjectStatus.PROTOTYPE, ProjectStatus.PILOT, ProjectStatus.IMPLEMENTED):
        projects, _ = ProjectRepository(db).list_projects(
            status=status, skip=0, limit=1
        )
        if projects:
            return projects[0]
    return None


def _ensure_offer(db, project, organization, partner):
    """Return the offer. Flushes but does not commit."""
    repo = SupportOfferRepository(db)
    existing = repo.list_for_project(project.id)
    if existing:
        return existing[0], False
    offer = repo.create(
        {
            "project_id": project.id,
            "organization_id": organization.id,
            "offered_by": partner.id,
            "support_type": OFFER["support_type"],
            "message": OFFER["message"],
            "status": SupportOfferStatus.OFFERED,
        }
    )
    return offer, True


def _ensure_impact_metrics(db, project):
    """Ensure the demo impact metrics exist on the project (idempotent).

    Stable lookup is project_id + metric name: existing metrics are kept
    untouched and never duplicated. Returns (created, preserved) counts.
    Flushes but does not commit.
    """
    repo = ImpactMetricRepository(db)
    existing_names = {m.name for m in repo.list_for_project(project.id)}
    created = 0
    preserved = 0
    for metric in IMPACT_METRICS:
        if metric["name"] in existing_names:
            preserved += 1
            continue
        repo.create(
            {
                "project_id": project.id,
                "name": metric["name"],
                "value": metric["value"],
                "unit": metric["unit"],
                "description": metric["description"],
            }
        )
        created += 1
    return created, preserved


def main() -> None:
    db = SessionLocal()
    try:
        partner, partner_created = _ensure_partner_user(db)
        db.commit()

        organization, org_created = _ensure_organization(db, partner)
        db.commit()

        project = _find_first_active_project(db)
        if project is None:
            print("=" * 64)
            print("CP5 demo seed: no project found.")
            print("No project exists yet. Accept a proposal first, then rerun")
            print("seed_cp5_demo.")
            print("=" * 64)
            return

        offer, offer_created = _ensure_offer(db, project, organization, partner)
        db.commit()

        impact_created, impact_preserved = _ensure_impact_metrics(db, project)
        db.commit()

        print("=" * 64)
        print("CP5 dev seed complete.")
        print(
            f"  partner user : {PARTNER_USER['email']} "
            f"({'created' if partner_created else 'already present'})"
        )
        print(f"  organization : {organization.name} "
              f"({'created' if org_created else 'already present'})")
        print(
            f"  project      : {project.title[:60]} "
            f"({'offer attached' if offer_created else 'already had an offer'})"
        )
        print(
            f"  impact       : {impact_created} metric(s) created, "
            f"{impact_preserved} already present"
        )
        print()
        print("Demo industry account:")
        print(f"  {PARTNER_USER['email']} ({PARTNER_USER['password']})")
        print()
        print(f"Project link (public):  project id {project.id}")
        print("=" * 64)
    finally:
        db.close()


if __name__ == "__main__":
    main()