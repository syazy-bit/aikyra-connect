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
    """The platform reviewer role does not grant team-creation rights.

    Reviewer is now a global platform role; it is not an institution
    membership role and does not imply an institution creator role. A
    platform reviewer with no active institution membership cannot create
    a team.
    """
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    # reviewer@aikyra.dev is a PLATFORM reviewer; it has no institution
    # creator role here, so team creation must be refused.
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


# --- Team detail authorization (HIGH #2) --------------------------------------


def test_get_team_malformed_uuid_returns_422(auth_client):
    """A malformed team id is rejected by path validation (422)."""
    response = auth_client.get("/api/teams/not-a-uuid")
    assert response.status_code == 422


def test_get_team_institution_owner_not_member_can_view(auth_client, user_client, db_session):
    """An ACTIVE owner of the team's institution can view a team even without
    a team membership."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    creator = user_client("creator@aikyra.dev")
    creator_uid = _user_id(db_session, "creator@aikyra.dev")
    _create_membership(
        db_session, creator_uid, uuid.UUID(inst["id"]), "student", "active"
    )
    team = _create_team(creator, inst["id"], ch["id"], name="OwnerView")

    # auth created the institution (active owner) but is NOT a team member.
    response = auth_client.get(f"/api/teams/{team['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == team["id"]


def test_get_team_institution_representative_not_member_can_view(
    auth_client, user_client, db_session
):
    """An ACTIVE representative of the team's institution can view a team
    even without a team membership."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    rep = user_client("rep@aikyra.dev")
    rep_uid = _user_id(db_session, "rep@aikyra.dev")
    _create_membership(
        db_session, rep_uid, uuid.UUID(inst["id"]), "representative", "active"
    )
    creator = user_client("creator2@aikyra.dev")
    creator_uid = _user_id(db_session, "creator2@aikyra.dev")
    _create_membership(
        db_session, creator_uid, uuid.UUID(inst["id"]), "student", "active"
    )
    team = _create_team(creator, inst["id"], ch["id"], name="RepView")

    response = rep.get(f"/api/teams/{team['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == team["id"]


def test_get_team_student_not_member_forbidden(auth_client, user_client, db_session):
    """A student at the institution who is not a team member cannot view a
    team's private details (only owners/representatives may)."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"], name="StudentNo")
    student = user_client("student@aikyra.dev")
    student_uid = _user_id(db_session, "student@aikyra.dev")
    _create_membership(
        db_session, student_uid, uuid.UUID(inst["id"]), "student", "active"
    )
    response = student.get(f"/api/teams/{team['id']}")
    assert response.status_code == 403


def test_get_team_owner_from_other_institution_forbidden(
    auth_client, user_client, db_session
):
    """An owner of a DIFFERENT institution cannot view a team belonging to
    another institution."""
    inst_a = _create_institution(auth_client, name="Inst A")
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst_a["id"], ch["id"], name="TeamA")
    outsider = user_client("outsider@aikyra.dev")
    outsider.get("/api/institutions")  # register
    inst_b = _create_institution(outsider, name="Inst B")  # outsider owns Inst B

    response = outsider.get(f"/api/teams/{team['id']}")
    assert response.status_code == 403


# --- Team listing multi-tenant isolation (MEDIUM #2) ---------------------------


def test_list_teams_empty_for_user_with_no_memberships(auth_client, user_client, db_session):
    """A user with no active institution or team memberships sees no teams."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="Hidden")
    outsider = user_client("listoutsider@aikyra.dev")

    response = outsider.get("/api/teams")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_list_teams_cross_institution_institution_id_cannot_bypass(
    auth_client, user_client, db_session
):
    """Passing an unrelated institution_id must not leak teams from a
    different institution."""
    inst_a = _create_institution(auth_client, name="Inst A")
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst_a["id"], ch["id"], name="PrivateA")
    outsider = user_client("listbypass@aikyra.dev")
    outsider.get("/api/institutions")  # register
    _create_institution(outsider, name="Inst B")  # outsider owns Inst B

    response = outsider.get(f"/api/teams?institution_id={inst_a['id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_teams_team_membership_does_not_grant_other_institution_access(
    auth_client, user_client, db_session
):
    """Being a member of one team does not reveal teams at institutions the
    user is not affiliated with."""
    inst_a = _create_institution(auth_client, name="Inst A")
    inst_b = _create_institution(auth_client, name="Inst B")
    ch = _create_challenge(auth_client)
    team_a = _create_team(auth_client, inst_a["id"], ch["id"], name="TeamAtA")
    _create_team(auth_client, inst_b["id"], ch["id"], name="TeamAtB")

    member = user_client("teammember@aikyra.dev")
    member_uid = _user_id(db_session, "teammember@aikyra.dev")
    membership = TeamMembership(
        id=uuid.uuid4(),
        team_id=uuid.UUID(team_a["id"]),
        user_id=member_uid,
        role=TeamRole.MEMBER,
        status=TeamMembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    db_session.commit()

    response = member.get("/api/teams")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == team_a["id"]


def test_list_teams_institution_member_sees_own_teams(auth_client, user_client, db_session):
    """An active institution member can list teams for their institution."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="V1")
    _create_team(auth_client, inst["id"], ch["id"], name="V2")
    member_user = user_client("viewer@aikyra.dev")
    member_uid = _user_id(db_session, "viewer@aikyra.dev")
    _create_membership(
        db_session, member_uid, uuid.UUID(inst["id"]), "student", "active"
    )

    response = member_user.get(f"/api/teams?institution_id={inst['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(i["institution_id"] == inst["id"] for i in body["items"])


# --- teams.created_by FK semantics (MEDIUM #1) ---------------------------------


def test_team_creator_deletion_restricted(auth_client, db_session):
    """Deleting a user who created a team is blocked (RESTRICT), not cascaded."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models.user import User

    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    _create_team(auth_client, inst["id"], ch["id"], name="CreatorLocked")
    creator_uid = _user_id(db_session, "auth@aikyra.dev")

    try:
        db_session.query(User).filter(User.id == creator_uid).delete()
        db_session.commit()
        raise AssertionError(
            "deleting a user who created a team should be restricted"
        )
    except IntegrityError:
        db_session.rollback()


def test_team_created_by_fk_is_restrict_not_cascade(auth_client):
    """The teams.created_by FK is RESTRICT (safe), not CASCADE."""
    from app.models.team import Team

    created_by_fks = [
        fk for fk in Team.__table__.c.created_by.foreign_keys
    ]
    assert created_by_fks
    for fk in created_by_fks:
        assert fk.ondelete == "RESTRICT"
