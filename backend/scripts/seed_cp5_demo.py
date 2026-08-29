"""Development-only CP5 demo seed — industry/NGO support scenario.

Ensures the complete Phase 6 (Industry/NGO support) demo scenario exists on
top of the existing Phase 4 seeds without touching university-side data:

1. Ensures a demo industry user (`partner@aikyra.dev`) exists. The account has
   NO institution membership — industry partners are not university members and
   the approved-solutions surface is public.
2. Ensures exactly one organization managed by that user (so `POST
   /api/projects/{id}/offers` works for the demo login).
3. Finds the first active project (materialized by the accept → project hook)
   and ensures exactly one support offer (SolarNova Foundation · mentorship)
   on it, so the "Approved Solutions → project → offer" story can be shown
   immediately from both the university and industry sides.

Deliberately does NOT create projects: project materialization belongs to the
proposal accept hook, never to a seed script. If no active project exists yet,
the script prints a warning and exits cleanly.

Idempotent: safe to run repeatedly. Users, organizations and offers are reused
if they already exist; no duplicates are ever created. Never referenced by
Alembic; never executed by application startup.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_cp5_demo
"""

from app.core.database import SessionLocal
from app.models.project import ProjectStatus
from app.models.support_offer import SupportOfferStatus, SupportType
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
    """Return the most recently created active project, or None."""
    projects, _ = ProjectRepository(db).list_projects(
        status=ProjectStatus.ACTIVE, skip=0, limit=1
    )
    return projects[0] if projects else None


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
            print("CP5 demo seed: no active project found.")
            print("Projects are materialized by the proposal accept hook only.")
            print("Accept a proposal (proposal review -> accept) and re-run this")
            print("script to attach the demo support offer.")
            print("=" * 64)
            return

        offer, offer_created = _ensure_offer(db, project, organization, partner)
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