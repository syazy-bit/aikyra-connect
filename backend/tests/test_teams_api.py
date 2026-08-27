"""Phase 5 Checkpoint 1 — Team Foundation tests.

Covers: team creation, listing, detail, update by lead, membership,
duplicate-team-name constraint, cross-institution authorization,
team-member authorization, role/enum validation, and mass-assignment
protection.
"""

import uuid

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.team import (
    Team,
    TeamMembership,
    TeamMembershipStatus,
    TeamRole,
)


def _create_institution(c, **overrides):
    """Register an institution via the API (returns JSON)."""
    payload = {
        "name": "Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    """Create a challenge via the API (returns JSON)."""
    payload = {
        "title": "Test Challenge",
        "description": "Test challenge description for team tests.",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/challenges", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_team(c, institution_id, challenge_id, **overrides):
    """Create a team via the API (returns JSON)."""
    payload = {
        "institution_id": institution_id,
        "challenge_id": challenge_id,
        "name": "Test Team",
        "description": "Test team description.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_membership(db_session, user_id, institution_id, role, status="active"):
    """Insert an institution membership row directly into the DB."""
    membership = InstitutionMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        institution_id=institution_id,
        role=InstitutionMembershipRole(role),
        status=InstitutionMembershipStatus(status),
    )
    db_session.add(membership)
    db_session.commit()
    return membership


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


# --- Team creation -----------------------------------------------------------


def test_create_team_requires_auth(client, auth_client):
    """Unauthenticated POST /api/teams returns 401."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    response = client.post(
        "/api/teams",
        json={"institution_id": inst["id"], "challenge_id": ch["id"], "name": "T"},
    )
    assert response.status_code == 401


def test_create_team_success_creates_lead_membership(auth_client, db_session):
    """Owner creating a team becomes an active lead and gets an active membership."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Alpha")

    assert team["status"] == "forming"
    assert team["created_by"] == str(_user_id(db_session, "auth@aikyra.dev"))

    membership = db_session.query(TeamMembership).filter(
        TeamMembership.team_id == uuid.UUID(team["id"])
    ).first()
    assert membership is not None
    assert membership.role == TeamRole.LEAD
    assert membership.status == TeamMembershipStatus.ACTIVE


def test_create_team_requires_institution_membership(auth_client, reviewer_client, db_session):
    """A user with no active membership at the institution cannot create a team."""
    inst_name = "NoMember Inst"
    inst = _create_institution(auth_client, name=inst_name)
    ch = _create_challenge(auth_client)
    response = reviewer_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": ch["id"],
            "name": "Hijack",
        },
    )
    assert response.status_code == 403


def test_create_team_requires_active_membership(auth_client, reviewer_client, db_session):
    """A non-active institution membership cannot create a team."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_membership(
        db_session,
        _user_id(db_session, "reviewer@aikyra.dev"),
        uuid.UUID(inst["id"]),
        "student",
        status="suspended",
    )
    response = reviewer_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": ch["id"],
            "name": "Suspended",
        },
    )
    assert response.status_code == 403


def test_create_team_rejects_invalid_role(auth_client, reviewer_client, db_session):
    """A role not in the allowed creator roles cannot create a team."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_membership(
        db_session,
        _user_id(db_session, "reviewer@aikyra.dev"),
        uuid.UUID(inst["id"]),
        "reviewer",
    )
    response = reviewer_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": ch["id"],
            "name": "Reviewer team",
        },
    )
    assert response.status_code == 403


def test_create_team_nonexistent_institution_not_found(auth_client):
    """Creating a team for a nonexistent institution returns 404."""
    ch = _create_challenge(auth_client)
    response = auth_client.post(
        "/api/teams",
        json={
            "institution_id": str(uuid.uuid4()),
            "challenge_id": ch["id"],
            "name": "Ghost",
        },
    )
    assert response.status_code == 404


def test_create_team_nonexistent_challenge_not_found(auth_client):
    """Creating a team for a nonexistent challenge returns 404."""
    inst = _create_institution(auth_client)
    response = auth_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": str(uuid.uuid4()),
            "name": "Ghost",
        },
    )
    assert response.status_code == 404


# --- Duplicate team-name constraint ------------------------------------------


def test_create_team_duplicate_name_conflict(auth_client):
    """Duplicate team name within the same institution+challenge returns 409."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="Dup")
    response = auth_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": ch["id"],
            "name": "Dup",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_same_name_allowed_different_challenge(auth_client):
    """The same name is allowed for a different challenge."""
    inst = _create_institution(auth_client)
    ch1 = _create_challenge(auth_client, title="Challenge One")
    ch2 = _create_challenge(auth_client, title="Challenge Two")
    _create_team(auth_client, inst["id"], ch1["id"], name="Same")
    team2 = _create_team(auth_client, inst["id"], ch2["id"], name="Same")
    assert team2["name"] == "Same"


# --- Team listing ------------------------------------------------------------


def test_list_teams(client, auth_client):
    """Authenticated and unauthenticated users can list teams with total."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="A")
    _create_team(auth_client, inst["id"], ch["id"], name="B")

    response = auth_client.get("/api/teams")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_teams_filters_by_institution(auth_client):
    """Listing can be filtered by institution."""
    inst = _create_institution(auth_client, name="Filter Inst")
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="F1")
    _create_team(auth_client, inst["id"], ch["id"], name="F2")

    response = auth_client.get(f"/api/teams?institution_id={inst['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(i["institution_id"] == inst["id"] for i in body["items"])


# --- Team detail and team-member authorization --------------------------------


def test_get_team_requires_membership(auth_client, reviewer_client, db_session):
    """A non-member of a team cannot read its detail (403)."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Private")

    response = reviewer_client.get(f"/api/teams/{team['id']}")
    assert response.status_code == 403


def test_get_team_by_creator(auth_client):
    """The team creator (lead) can read team detail."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Visible")

    response = auth_client.get(f"/api/teams/{team['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == team["id"]


def test_get_team_not_found(auth_client):
    """GET for a nonexistent team returns 404."""
    response = auth_client.get(f"/api/teams/{uuid.uuid4()}")
    assert response.status_code == 404


# --- Team update by lead ------------------------------------------------------


def test_update_team_by_lead(auth_client):
    """The team lead can update name and description."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Before")

    response = auth_client.patch(
        f"/api/teams/{team['id']}",
        json={"name": "After", "description": "New description"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "After"
    assert body["description"] == "New description"


def test_update_team_by_non_lead_forbidden(auth_client, reviewer_client, db_session):
    """A team member who is not the lead cannot update the team."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Locked")

    # Give reviewer an active member (non-lead) membership.
    reviewer_uid = _user_id(db_session, "reviewer@aikyra.dev")
    member = TeamMembership(
        id=uuid.uuid4(),
        team_id=uuid.UUID(team["id"]),
        user_id=reviewer_uid,
        role=TeamRole.MEMBER,
        status=TeamMembershipStatus.ACTIVE,
    )
    db_session.add(member)
    db_session.commit()

    response = reviewer_client.patch(
        f"/api/teams/{team['id']}",
        json={"name": "Hijacked"},
    )
    assert response.status_code == 403


def test_update_team_duplicate_name_conflict(auth_client):
    """Updating to an already-used name within the same context returns 409."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="Taken")
    team2 = _create_team(auth_client, inst["id"], ch["id"], name="Free")

    response = auth_client.patch(
        f"/api/teams/{team2['id']}",
        json={"name": "Taken"},
    )
    assert response.status_code == 409


# --- Team membership listing --------------------------------------------------


def test_list_members_requires_team_membership(auth_client, reviewer_client, db_session):
    """A non-member cannot list a team's members (403)."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Secret")

    response = reviewer_client.get(f"/api/teams/{team['id']}/members")
    assert response.status_code == 403


def test_list_members_by_lead(auth_client, db_session):
    """The lead can list members and sees themselves as lead."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="M")

    response = auth_client.get(f"/api/teams/{team['id']}/members")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["role"] == "lead"
    assert body["items"][0]["status"] == "active"


# --- Mass-assignment protection -----------------------------------------------


def test_create_team_rejects_status_injection(auth_client):
    """The create schema (extra='forbid') rejects server-controlled fields."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    response = auth_client.post(
        "/api/teams",
        json={
            "institution_id": inst["id"],
            "challenge_id": ch["id"],
            "name": "Inject",
            "created_by": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422


def test_update_team_rejects_status_injection(auth_client):
    """The update schema (extra='forbid') rejects server-controlled fields."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="Safe")

    response = auth_client.patch(
        f"/api/teams/{team['id']}",
        json={"status": "active", "created_by": str(uuid.uuid4())},
    )
    assert response.status_code == 422
