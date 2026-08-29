"""Phase 7 Checkpoint 6 — Project lifecycle (prototype -> pilot -> implemented).

Covers: the lifecycle authorization matrix (only the project team's ACTIVE
lead may advance — team members, unrelated users, institution owners who are
not on the team, and platform reviewers all get 403; anonymous gets 401),
valid and invalid transitions (409 for every non-forward move), 404 for
unknown projects, strict request validation (extra="forbid", malformed status
-> 422), the mass-assignment/impersonation guard (identity fields are rejected,
never trusted), and CP4/CP5 regression (proposal acceptance still materializes
a project that starts at 'prototype', and support offers keep working through
pilot while the terminal 'implemented' state stops new offers).

All authorization is derived from the database at request time — never from
client input.
"""

import uuid
from datetime import datetime, timezone

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.team import TeamMembership, TeamMembershipStatus, TeamRole


def _create_institution(c, **overrides):
    payload = {
        "name": "CP6 Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": "CP6 Test Challenge",
        "description": "Test challenge description for CP6 lifecycle tests.",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/challenges", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_team(c, institution_id, challenge_id, **overrides):
    payload = {
        "institution_id": institution_id,
        "challenge_id": challenge_id,
        "name": "CP6 Test Team",
        "description": "Test team description.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_proposal(c, team_id, challenge_id, **overrides):
    payload = {
        "team_id": team_id,
        "challenge_id": challenge_id,
        "title": "CP6 Test Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_membership(db_session, user_id, institution_id, role, status="active"):
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


def _add_team_member(db_session, team_id, user_id, role="member", status="active"):
    membership = TeamMembership(
        id=uuid.uuid4(),
        team_id=team_id,
        user_id=user_id,
        role=TeamRole(role),
        status=TeamMembershipStatus(status),
        invited_by=None,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(membership)
    db_session.commit()
    return membership


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _register_user(db_session, user_client, email, **membership):
    """Register a user; optionally give them an institution membership row."""
    user_client(email)
    uid = _user_id(db_session, email)
    if membership:
        _create_membership(db_session, uid, **membership)
    return uid


def _project_with_member(db_session, auth_client, user_client):
    """Full CP6 fixture: accepted project (prototype) whose team has a lead
    (auth_client) and an ordinary member (member@aikyra.dev)."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
        ).status_code
        == 200
    )
    resp = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert resp.status_code == 200, resp.json()

    member_uid = _register_user(db_session, user_client, "member@aikyra.dev")
    _add_team_member(db_session, team["id"], member_uid)

    _register_user(db_session, user_client, "owner@aikyra.dev")
    inst_owner_uid = _user_id(db_session, "owner@aikyra.dev")
    _create_membership(
        db_session, inst_owner_uid, uuid.UUID(inst["id"]), "owner", "active"
    )

    project = auth_client.get("/api/projects").json()["items"][0]
    return project, member_uid, inst


def _project(auth_client):
    """Accepted project (prototype) with no extra team members."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
        ).status_code
        == 200
    )
    resp = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert resp.status_code == 200, resp.json()
    return auth_client.get("/api/projects").json()["items"][0]


def _patch_lifecycle(client, pid, status=None, **extra):
    body = {} if status is None else {"status": status}
    body.update(extra)
    return client.patch(f"/api/projects/{pid}/lifecycle", json=body)


# --- Authentication -----------------------------------------------------------


def test_lifecycle_requires_auth(client, auth_client):
    project = _project(auth_client)
    resp = _patch_lifecycle(client, project["id"], "pilot")
    assert resp.status_code == 401


def test_team_lead_can_advance_to_pilot(auth_client):
    project = _project(auth_client)
    resp = _patch_lifecycle(auth_client, project["id"], "pilot")
    assert resp.status_code == 200, resp.json()
    assert resp.json()["status"] == "pilot"


def test_team_member_cannot_advance(db_session, auth_client, user_client):
    project, member_uid, _ = _project_with_member(db_session, auth_client, user_client)
    member_client = user_client("member@aikyra.dev")
    resp = _patch_lifecycle(member_client, project["id"], "pilot")
    assert resp.status_code == 403


def test_unrelated_user_cannot_advance(db_session, auth_client, user_client):
    project = _project(auth_client)
    _register_user(db_session, user_client, "stranger@aikyra.dev")
    stranger = user_client("stranger@aikyra.dev")
    resp = _patch_lifecycle(stranger, project["id"], "pilot")
    assert resp.status_code == 403


def test_institution_owner_who_is_not_lead_cannot_advance(
    db_session, auth_client, user_client
):
    project, _, _ = _project_with_member(db_session, auth_client, user_client)
    owner = user_client("owner@aikyra.dev")
    resp = _patch_lifecycle(owner, project["id"], "pilot")
    assert resp.status_code == 403


def test_platform_reviewer_who_is_not_lead_cannot_advance(
    db_session, auth_client, user_client, reviewer_client
):
    project = _project(auth_client)
    resp = _patch_lifecycle(reviewer_client, project["id"], "pilot")
    assert resp.status_code == 403


# --- Valid transitions --------------------------------------------------------


def test_full_forward_sequence_lead(auth_client):
    """prototype -> pilot -> implemented all succeed in sequence."""
    project = _project(auth_client)
    assert project["status"] == "prototype"

    to_pilot = _patch_lifecycle(auth_client, project["id"], "pilot")
    assert to_pilot.status_code == 200, to_pilot.json()
    assert to_pilot.json()["status"] == "pilot"

    to_implemented = _patch_lifecycle(auth_client, project["id"], "implemented")
    assert to_implemented.status_code == 200, to_implemented.json()
    assert to_implemented.json()["status"] == "implemented"


def test_lead_advancing_pilot_to_implemented_200(auth_client):
    project = _project(auth_client)
    assert _patch_lifecycle(auth_client, project["id"], "pilot").status_code == 200
    resp = _patch_lifecycle(auth_client, project["id"], "implemented")
    assert resp.status_code == 200
    assert resp.json()["status"] == "implemented"


# --- Invalid transitions ------------------------------------------------------


def test_prototype_to_implemented_409(auth_client):
    project = _project(auth_client)
    resp = _patch_lifecycle(auth_client, project["id"], "implemented")
    assert resp.status_code == 409


def test_pilot_to_prototype_409(auth_client):
    project = _project(auth_client)
    _patch_lifecycle(auth_client, project["id"], "pilot")
    resp = _patch_lifecycle(auth_client, project["id"], "prototype")
    assert resp.status_code == 409


def test_implemented_state_is_terminal(auth_client):
    project = _project(auth_client)
    _patch_lifecycle(auth_client, project["id"], "pilot")
    _patch_lifecycle(auth_client, project["id"], "implemented")

    resp = _patch_lifecycle(auth_client, project["id"], "prototype")
    assert resp.status_code == 409
    resp = _patch_lifecycle(auth_client, project["id"], "pilot")
    assert resp.status_code == 409
    resp = _patch_lifecycle(auth_client, project["id"], "implemented")
    assert resp.status_code == 409


# --- Resource -----------------------------------------------------------------


def test_unknown_project_404(auth_client):
    resp = _patch_lifecycle(auth_client, uuid.uuid4(), "pilot")
    assert resp.status_code == 404


# --- Request validation -------------------------------------------------------


def test_malformed_status_422(auth_client):
    project = _project(auth_client)
    resp = _patch_lifecycle(auth_client, project["id"], "not_a_status")
    assert resp.status_code == 422


def test_missing_status_422(auth_client):
    project = _project(auth_client)
    resp = _patch_lifecycle(auth_client, project["id"])
    assert resp.status_code == 422


def test_extra_fields_rejected_422(auth_client):
    project = _project(auth_client)
    for field, value in [
        ("team_id", uuid.uuid4()),
        ("institution_id", uuid.uuid4()),
        ("proposal_id", uuid.uuid4()),
        ("project_id", uuid.uuid4()),
        ("user_id", uuid.uuid4()),
        ("created_by", uuid.uuid4()),
    ]:
        resp = _patch_lifecycle(auth_client, project["id"], "pilot", **{field: str(value)})
        assert resp.status_code == 422, (field, resp.json())


def test_client_cannot_impersonate_or_reassign(auth_client):
    project = _project(auth_client)
    imposter = str(uuid.uuid4())
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle",
        json={
            "status": "pilot",
            "user_id": imposter,
            "team_id": str(uuid.uuid4()),
            "proposal_id": str(uuid.uuid4()),
            "institution_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


# --- Regression: CP4 accept hook + CP5 support offers -------------------------


def test_accepting_proposal_creates_project_at_prototype(auth_client):
    project = _project(auth_client)
    assert project["status"] == "prototype"

    detail = auth_client.get(f"/api/projects/{project['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "prototype"


def test_support_offers_continue_working_until_implemented(auth_client):
    """CP5 regression: offers work on prototype and pilot, stop once
    implemented (the terminal lifecycle state)."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    auth_client.post(f"/api/proposals/{proposal['id']}/review", json={"action": "accept"})
    project = auth_client.get("/api/projects").json()["items"][0]

    mgr = auth_client
    mgr.post("/api/organizations", json={"name": "Lifecycle FundCorp"})
    offer = mgr.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "funding", "message": "Prototype funding."},
    )
    assert offer.status_code == 201, offer.json()

    _patch_lifecycle(auth_client, project["id"], "pilot")
    offer_pilot = mgr.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "mentorship", "message": "Pilot mentorship."},
    )
    assert offer_pilot.status_code == 201, offer_pilot.json()

    _patch_lifecycle(auth_client, project["id"], "implemented")
    offer_done = mgr.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "equipment", "message": "Too late."},
    )
    assert offer_done.status_code == 409