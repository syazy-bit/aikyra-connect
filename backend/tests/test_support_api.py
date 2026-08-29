"""Phase 6 — Industry/NGO support (projects, organizations, support offers).

Covers: the accept -> project materialization hook, public project listing and
detail, organization registration (server-set manager, duplicate-name 409),
and support-offer creation authorization (only the org's manager may offer;
org/offered_by/status are server-set and never client-supplied; forged fields
are 422; non-managers 403; anonymous 401; non-existent project 404).
"""

import uuid


def _create_institution(c, **overrides):
    payload = {
        "name": "Support Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": "Support Test Challenge",
        "description": "Test challenge description.",
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
        "name": "Support Test Team",
        "description": "Test team.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_proposal(c, team_id, challenge_id, **overrides):
    payload = {
        "team_id": team_id,
        "challenge_id": challenge_id,
        "title": "Support Test Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _accepted_project(auth_client):
    """Create an institution + challenge + team with an accepted proposal
    (and thus a materialized project). Returns (inst, ch, team, proposal)."""
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
    return inst, ch, team, proposal


def _register_org(client, email=None, name="SolarCorp", **overrides):
    """Register an org. `client` may be a user_client factory (called with
    email) or an already-authenticated TestClient (used directly)."""
    c = client(email) if callable(client) else client
    payload = {"name": name, **overrides}
    resp = c.post("/api/organizations", json=payload)
    assert resp.status_code == 201, resp.json()
    return c, resp.json()


# --- Accept -> Project materialization hook ----------------------------------


def test_accepting_proposal_creates_project(auth_client):
    """Accepting a submission materializes a project for it."""
    inst, ch, team, proposal = _accepted_project(auth_client)
    listing = auth_client.get("/api/projects")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == proposal["title"]
    assert items[0]["institution_name"] == inst["name"]
    assert items[0]["team_name"] == team["name"]
    assert items[0]["challenge_title"] == ch["title"]
    assert items[0]["offer_count"] == 0


def test_rejected_proposal_does_not_create_project(auth_client):
    """Rejecting a proposal must NOT create a project."""
    inst, ch, team = _create_institution(auth_client), None, None
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    resp = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
    )
    assert resp.status_code == 200
    listing = auth_client.get("/api/projects").json()
    assert listing["total"] == 0


# --- Public project surface --------------------------------------------------


def test_projects_are_public_without_auth(client, auth_client):
    """Anonymous users can list and read approved projects and their offers."""
    inst, ch, team, proposal = _accepted_project(auth_client)
    project = client.get("/api/projects").json()["items"][0]

    # Offer something first so the detail shows it.
    _register_org(auth_client, "org-manager@aikyra.dev")
    resp = auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "funding", "message": "We can help fund this."},
    )
    assert resp.status_code == 201, resp.json()

    detail = client.get(f"/api/projects/{project['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == proposal["title"]
    assert len(body["offers"]) == 1
    assert body["offers"][0]["organization"]["name"] == "SolarCorp"
    assert body["offers"][0]["support_type"] == "funding"
    assert body["offers"][0]["message"] == "We can help fund this."
    assert body["offers"][0]["status"] == "offered"


def test_project_detail_unknown_404(client):
    resp = client.get(f"/api/projects/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_public_projects_require_no_auth(client, auth_client):
    inst, ch, team, proposal = _accepted_project(auth_client)
    resp = client.get("/api/projects")
    assert resp.status_code == 200


# --- Organization registration ------------------------------------------------


def test_register_organization_sets_manager(auth_client):
    """Registration sets manager_user_id server-side to the caller."""
    resp = auth_client.post(
        "/api/organizations",
        json={"name": "Acme Industries", "description": "An industry partner."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["manager_user_id"] is not None

    me = auth_client.get("/api/organizations/me").json()
    assert me["organization"]["name"] == "Acme Industries"
    assert me["organization"]["description"] == "An industry partner."


def test_duplicate_org_name_409(auth_client, user_client):
    """A duplicate normalized organization name returns 409."""
    _register_org(user_client, "dup1@aikyra.dev", name="SameCorp")
    resp = user_client("dup2@aikyra.dev").post(
        "/api/organizations", json={"name": "  samecorp!! "}
    )
    assert resp.status_code == 409


def test_register_org_requires_auth(client):
    resp = client.post("/api/organizations", json={"name": "AnonCorp"})
    assert resp.status_code == 401


def test_register_org_rejects_forged_manager(auth_client):
    # manager_user_id is not an accepted field -> 422 (mass-assignment block).
    resp = auth_client.post(
        "/api/organizations",
        json={"name": "ForgeCorp", "manager_user_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


# --- Support offer authorization ----------------------------------------------


def test_non_manager_cannot_offer(auth_client, user_client):
    """A user who manages no organization cannot offer support (403)."""
    inst, ch, team, proposal = _accepted_project(auth_client)
    project = auth_client.get("/api/projects").json()["items"][0]

    other = user_client("plain-user@aikyra.dev")
    resp = other.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "equipment", "message": "Highjacked offer"},
    )
    assert resp.status_code == 403


def test_offer_requires_auth(client, auth_client):
    inst, ch, team, proposal = _accepted_project(auth_client)
    project = auth_client.get("/api/projects").json()["items"][0]
    resp = client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "mentorship", "message": "anon"},
    )
    assert resp.status_code == 401


def test_offer_rejects_forged_organization_and_status(auth_client):
    """Clients cannot forge organization_id, offered_by or status (422)."""
    inst, ch, team, proposal = _accepted_project(auth_client)
    project = auth_client.get("/api/projects").json()["items"][0]
    c, org = _register_org(auth_client, "forge-org@aikyra.dev")

    # Forged organization_id (UUID shape) is not accepted by the schema.
    resp = c.post(
        f"/api/projects/{project['id']}/offers",
        json={
            "support_type": "funding",
            "organization_id": str(uuid.uuid4()),
            "offered_by": str(uuid.uuid4()),
            "status": "accepted",
        },
    )
    assert resp.status_code == 422


def test_offer_on_unknown_project_404(auth_client):
    _register_org(auth_client, "unknown-proj-org@aikyra.dev")
    resp = auth_client.post(
        f"/api/projects/{uuid.uuid4()}/offers",
        json={"support_type": "pilot_support", "message": "hello"},
    )
    assert resp.status_code == 404


def test_manager_offer_sets_org_offered_by_status(auth_client):
    """A successful offer derives org/offered_by server-side and is 'offered'."""
    inst, ch, team, proposal = _accepted_project(auth_client)
    project = auth_client.get("/api/projects").json()["items"][0]
    c, org = _register_org(auth_client, "total-manager@aikyra.dev", name="FundCorp")

    resp = c.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "funding", "message": "   "},
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["organization_id"] == org["id"]
    assert body["offered_by"] == org["manager_user_id"]
    assert body["status"] == "offered"
    assert body["message"] is None  # blank whitespace message stripped to null
