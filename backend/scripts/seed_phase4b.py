"""Development-only Phase 4B demo seed.

Creates realistic institutions and challenges so the deterministic matching
engine can be demonstrated before the authentication/verification phase
exists. Selected DEV SEED institutions are marked `verified` directly via
the ORM — this is demo data only and introduces no production verification
bypass: the public API still cannot verify anything.

Usage (from backend/):
    .venv\\Scripts\\python.exe -m scripts.seed_phase4b

Idempotent: rows with the same names/titles are skipped on re-runs.
Never referenced by Alembic; never executed by application startup.
"""

from app.core.database import SessionLocal
from app.models.challenge import Challenge
from app.models.institution import (
    Institution,
    InstitutionStatus,
    InstitutionType,
    InstitutionVerificationStatus,
)
from app.models.institution_membership import (
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.repositories.membership_repository import MembershipRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import pwd_context
from app.services.challenge_service import ChallengeService
from app.services.problem_dna_service import ProblemDnaService

INSTITUTIONS = [
    {
        "name": "Coastal Institute of Rural Technology",
        "institution_type": InstitutionType.UNIVERSITY,
        "location": "Anantapur, Andhra Pradesh",
        "description": (
            "Public engineering university focused on rural water "
            "infrastructure and agricultural technology."
        ),
        "website": "https://cirt-example.edu.in",
        "contact_email": "hello@cirt-example.edu.in",
        "domains": ["water_sanitation", "agriculture", "energy"],
        "capabilities": {
            "departments": ["Civil Engineering", "Computer Science"],
            "expertise": ["Hydrology", "IoT sensing", "GIS"],
            "disciplines": ["Environmental Engineering"],
            "research_areas": ["Low-cost water quality monitoring"],
            "technologies": ["Remote sensing", "Solar micro-grids"],
            "facilities": ["Water Testing Lab", "Electronics Prototyping Lab"],
            "project_experience": ["Village borewell audit program, Anantapur 2025"],
            "collaboration_modes": ["Student projects", "Field pilots"],
        },
        "verified": True,
    },
    {
        "name": "National Institute of Rural Health Sciences",
        "institution_type": InstitutionType.RESEARCH_INSTITUTE,
        "location": "Hyderabad, Telangana",
        "description": "Research institute for public health delivery in rural districts.",
        "domains": ["healthcare", "water_sanitation"],
        "capabilities": {
            "expertise": ["public health", "epidemiology", "water quality"],
            "research_areas": ["Contaminated drinking water interventions"],
            "facilities": ["Water quality analysis laboratory"],
            "project_experience": ["District sanitation survey 2024"],
        },
        "verified": True,
    },
    {
        "name": "Sunrise Engineering College",
        "institution_type": InstitutionType.COLLEGE,
        "location": "Tumakuru, Karnataka",
        "description": "Undergraduate engineering college with strong energy labs.",
        "domains": ["energy", "education"],
        "capabilities": {
            "departments": ["Electrical Engineering"],
            "expertise": ["renewable energy", "power systems"],
            "technologies": ["solar", "smart metering"],
            "facilities": ["Power Systems Lab"],
        },
        "verified": True,
    },
    {
        "name": "Agri Tech Innovation Hub",
        "institution_type": InstitutionType.INNOVATION_HUB,
        "location": "Tumakuru, Karnataka",
        "description": "Incubation hub for farmer-facing technology ventures.",
        "domains": ["agriculture", "rural_livelihoods"],
        "capabilities": {
            "expertise": ["agronomy", "IoT sensing"],
            "innovation_support": ["incubation", "mentorship"],
            "prototyping": ["3D printing", "electronics bench"],
            "project_experience": ["Soil moisture pilot with farmer groups"],
        },
        "verified": True,
    },
    {
        "name": "Metro City University",
        "institution_type": InstitutionType.UNIVERSITY,
        "location": "Bengaluru, Karnataka",
        "description": "Urban research university covering city systems.",
        "domains": ["urban_development", "waste_management", "transportation"],
        "capabilities": {
            "expertise": ["urban planning", "waste processing"],
            "research_areas": ["Waste segregation automation"],
            "facilities": ["Materials Lab"],
        },
        "verified": True,
    },
    {
        "name": "AccessAbility Design School",
        "institution_type": InstitutionType.COLLEGE,
        "location": "Chennai, Tamil Nadu",
        "description": "Design college specialising in inclusive infrastructure.",
        "domains": ["accessibility", "education"],
        "capabilities": {
            "expertise": ["universal design", "assistive technology"],
            "facilities": ["Accessibility auditing studio"],
        },
        # Deliberately left UNVERIFIED to demonstrate matching exclusion.
        "verified": False,
    },
    {
        "name": "Rural Livelihoods Research Foundation",
        "institution_type": InstitutionType.RESEARCH_INSTITUTE,
        "location": "Bhopal, Madhya Pradesh",
        "description": "Studies livelihood generation and skill development.",
        "domains": ["rural_livelihoods", "education"],
        "capabilities": {"expertise": ["rural development", "economics"]},
        "verified": False,
    },
    {
        "name": "Digital Bridge Innovation Hub",
        "institution_type": InstitutionType.INNOVATION_HUB,
        "location": "Kochi, Kerala",
        "description": "Hub for digital inclusion and connectivity projects.",
        "domains": ["digital_services", "education"],
        "capabilities": {"expertise": ["software engineering", "networking"]},
        "verified": False,
    },
]

CHALLENGES = [
    {
        "title": "Village borewells failing every summer",
        "description": (
            "Our village borewells run dry and the drinking water is often "
            "contaminated. Four hundred farming families lose crops and "
            "depend on expensive water tankers. Sanitation near the wells is "
            "also poor."
        ),
        "location": "Anantapur, Andhra Pradesh",
    },
    {
        "title": "Frequent power cuts hurt village students",
        "description": (
            "Daily power cuts and a failing transformer leave streets dark "
            "and children unable to study. Solar street lighting would help "
            "the whole community."
        ),
        "location": "Tumakuru, Karnataka",
    },
    {
        "title": "Uncollected garbage spreading disease in Ward 6",
        "description": (
            "Household waste is not collected for weeks. Plastic and rotting "
            "garbage pile up near homes, creating a health hazard for "
            "residents."
        ),
        "location": "Bengaluru, Karnataka",
    },
    {
        "title": "Farmers lack timely crop price information",
        "description": (
            "Farmers sell at low prices because they cannot compare mandi "
            "rates. A simple market price information service would raise "
            "incomes across many villages."
        ),
        "location": "Anantapur, Andhra Pradesh",
    },
]

# --- Demo users and memberships for Phase 4C -------------------------------
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


def main() -> None:
    db = SessionLocal()
    created_institutions = 0
    skipped_institutions = 0
    try:
        # --- Institutions (ORM; dev-only verification marks) --------------
        for spec in INSTITUTIONS:
            exists = (
                db.query(Institution)
                .filter(Institution.name == spec["name"])
                .first()
            )
            if exists:
                skipped_institutions += 1
                continue
            verified = spec.pop("verified")
            institution = Institution(
                **spec,
                status=InstitutionStatus.ACTIVE,
                verification_status=(
                    InstitutionVerificationStatus.VERIFIED
                    if verified
                    else InstitutionVerificationStatus.UNVERIFIED
                ),
                verification_note="DEV SEED — not a production verification." if verified else None,
            )
            db.add(institution)
            created_institutions += 1
        db.commit()

        # --- Challenges + DNA through the REAL classifier pipeline ---------
        challenge_service = ChallengeService(db)
        dna_service = ProblemDnaService(db)
        created_challenges = []
        for payload in CHALLENGES:
            exists = (
                db.query(Challenge)
                .filter(Challenge.title == payload["title"])
                .first()
            )
            if exists:
                continue
            challenge = challenge_service.create_challenge(_Payload(payload))
            dna, regenerated = dna_service.analyze_challenge(challenge.id)
            created_challenges.append((challenge, dna))

        # --- Demo users and memberships (Phase 4C) ---------------------------
        def _ensure_user(db, email: str, password: str, full_name: str, is_platform_reviewer: bool = False):
            repo = UserRepository(db)
            user = repo.get_by_email(email)
            if user is not None:
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

        # Find ADTU (created in seed_local_demo or seed_phase4b run)
        adtu = db.query(Institution).filter(Institution.name == "Assam Down Town University").first()
        if adtu is not None:
            users_created = users_reused = 0
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

            memberships_created = memberships_reused = 0
            for spec in DEMO_MEMBERSHIPS:
                user = user_map[spec["email"]]
                _, created = _ensure_membership(db, user, adtu, spec["role"])
                if created:
                    memberships_created += 1
                else:
                    memberships_reused += 1
            db.commit()

            print(
                f"  users:       {users_created} created, "
                f"{users_reused} already present"
            )
            print(
                f"  memberships: {memberships_created} created, "
                f"{memberships_reused} already present"
            )

        # --- Summary ---------------------------------------------------------
        print("=" * 64)
        print("Phase 4B dev seed complete.")
        print(
            f"  institutions: {created_institutions} created, "
            f"{skipped_institutions} already present"
        )
        print(f"  challenges:   {len(created_challenges)} created (DNA generated "
              "via RuleBasedClassifier)")
        for challenge, dna in created_challenges:
            print(
                f"    - {challenge.title[:52]:<52} "
                f"[{dna.primary_domain} / conf={dna.confidence_score}]"
            )
        print()
        print("Demo URLs (backend running on :8000):")
        if created_challenges:
            demo_id = created_challenges[0][0].id
            print(f"  matches API : http://127.0.0.1:8000/api/challenges/{demo_id}/matches")
            print(f"  frontend UI : http://localhost:5173/challenges/{demo_id}")
        else:
            print("  (no new challenges created this run)")
        print("=" * 64)
    finally:
        db.close()


class _Payload:
    """Minimal stand-in for the Pydantic create schema used by
    ChallengeService.create_challenge(model_dump())."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self) -> dict:
        return dict(self._data)


if __name__ == "__main__":
    main()
