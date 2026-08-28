"""Development-only Phase 4C seed — demo users and ADTU memberships.

Creates platform reviewer and owner demo accounts with active memberships
for Assam Down Town University so the authentication, membership, and
verification workflow can be manually tested locally.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_phase4c

Idempotent: safe to run repeatedly. Users and memberships are reused
if they already exist. Never referenced by Alembic; never executed by
application startup.
"""

from app.core.database import SessionLocal
from app.models.institution import Institution
from app.models.institution_membership import (
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.repositories.membership_repository import MembershipRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import pwd_context

ADTU_NAME = "Assam Down Town University"

DEMO_USERS = [
    {
        "email": "reviewer@aikyra.dev",
        "password": "reviewer123",
        "full_name": "Demo Platform Reviewer",
        "is_platform_reviewer": True,
    },
    {
        "email": "owner@adtu.dev",
        "password": "owner123",
        "full_name": "ADTU Demo Owner",
        "is_platform_reviewer": False,
    },
]

DEMO_MEMBERSHIPS = [
    {
        "email": "owner@adtu.dev",
        "role": InstitutionMembershipRole.OWNER,
    },
    # Note: reviewer@aikyra.dev is a PLATFORM reviewer, not an institution member.
    # Platform reviewers verify institutions across the platform without
    # needing institution-specific memberships.
]


def _ensure_user(db, email: str, password: str, full_name: str, is_platform_reviewer: bool = False):
    """Return (user, created). Flushes but does not commit."""
    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if user is not None:
        # Update platform reviewer flag if needed
        if user.is_platform_reviewer != is_platform_reviewer:
            user.is_platform_reviewer = is_platform_reviewer
            db.flush()
        return user, False
    user = repo.create(
        {
            "email": email.lower(),
            "hashed_password": pwd_context.hash(password),
            "full_name": full_name,
            "is_platform_reviewer": is_platform_reviewer,
        }
    )
    return user, True


def _ensure_membership(db, user, institution, role):
    """Return (membership, created). Flushes but does not commit."""
    repo = MembershipRepository(db)
    membership = repo.get_membership(user.id, institution.id)
    if membership is not None:
        return membership, False
    membership = repo.create(
        {
            "user_id": user.id,
            "institution_id": institution.id,
            "role": role,
            "status": InstitutionMembershipStatus.ACTIVE,
        }
    )
    return membership, True


def main() -> None:
    db = SessionLocal()
    try:
        # --- 1. Find ADTU --------------------------------------------------
        adtu = db.query(Institution).filter(Institution.name == ADTU_NAME).first()
        if adtu is None:
            raise SystemExit(
                f"ERROR: expected institution '{ADTU_NAME}' not found; "
                "run seed_local_demo.py or seed_phase4b.py first."
            )

        # --- 2. Create demo users ------------------------------------------
        users_created = 0
        users_reused = 0
        user_map = {}
        for spec in DEMO_USERS:
            user, created = _ensure_user(
                db, spec["email"], spec["password"], spec["full_name"],
                spec.get("is_platform_reviewer", False)
            )
            user_map[spec["email"]] = user
            if created:
                users_created += 1
            else:
                users_reused += 1
        db.commit()

        # --- 3. Create memberships -----------------------------------------
        memberships_created = 0
        memberships_reused = 0
        for spec in DEMO_MEMBERSHIPS:
            user = user_map[spec["email"]]
            _, created = _ensure_membership(db, user, adtu, spec["role"])
            if created:
                memberships_created += 1
            else:
                memberships_reused += 1
        db.commit()

        # --- Summary -------------------------------------------------------
        print("=" * 64)
        print("Phase 4C dev seed complete.")
        print(
            f"  users:       {users_created} created, "
            f"{users_reused} already present"
        )
        print(
            f"  memberships: {memberships_created} created, "
            f"{memberships_reused} already present"
        )
        print()
        print("Demo accounts:")
        for spec in DEMO_USERS:
            reviewer_flag = " (platform reviewer)" if spec.get("is_platform_reviewer") else ""
            print(f"  {spec['email']} ({spec['password']}){reviewer_flag}")
        print("=" * 64)
    finally:
        db.close()


if __name__ == "__main__":
    main()
