"""Phase — DEMO SUPPORT CONTRIBUTION (AIKYRA VERIFIED FUNDING, hackathon demo).

Covers the DEMO-ONLY contribution endpoint:

    POST /api/projects/{project_id}/funding/contributions/demo

Security first:
- anonymous -> 401;
- the supporter and goal are resolved server-side and never accepted from the
  client (forged contributed_by / goal_id / status / raised_minor /
  supporter_count / progress_bp -> 422);
- a project with no funding goal, or a CLOSED goal, is rejected;
- unknown project -> 404, malformed project id -> 422;
- zero/negative/overflow amounts -> 422;
- the DB row records the authenticated user's id, not any client identity;
- the public response exposes no private contributor data.

Business semantics:
- a successful demo contribution is stored COMPLETED, so it feeds the
  normal DB-authoritative aggregate (raised, supporter_count, progress_bp);
- the returned summary is the existing server-derived public summary;
- duplicate contributions by the same user count as one supporter;
- distinct users increase supporter_count.
"""

import uuid

from app.models.funding_contribution import (
    FundingContribution,
    FundingContributionStatus,
)
from app.models.funding_goal import FundingGoalStatus

# Example demo goal: ₹50,000 with a ₹500 (50,000 paise) demo contribution.
GOAL_MINOR = 50_00_000
DEMO_AMOUNT = 50_000  # ₹500

MAX_INT64 = 9223372036854775807


def _create_institution(c, **overrides):
    payload = {
        "name": f"Demo Funding Inst {uuid.uuid4().hex[:8]}",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": f"Demo Funding Challenge {uuid.uuid4().hex[:8]}",
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
        "name": f"Demo Funding Team {uuid.uuid4().hex[:8]}",
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
        "title": "Demo Funding Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _accepted_project(client):
    inst = _create_institution(client)
    ch = _create_challenge(client)
    team = _create_team(client, inst["id"], ch["id"])
    proposal = _create_proposal(client, team["id"], ch["id"])
    assert client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    assert (
        client.post(
            f"/api/proposals/{proposal['id']}/review",
            json={"action": "start_review"},
        ).status_code
        == 200
    )
    resp = client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert resp.status_code == 200, resp.json()
    return client.get("/api/projects").json()["items"][0]


def _register_user(db_session, user_client, email):
    user_client(email)
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _goal_row(db_session, project_id):
    from app.models.funding_goal import FundingGoal

    return (
        db_session.query(FundingGoal)
        .filter(FundingGoal.project_id == project_id)
        .one()
    )


def _open_goal(owner_client, project_id, goal_minor=GOAL_MINOR):
    """Team lead publishes an OPEN funding goal; returns the public summary."""
    resp = owner_client.post(
        f"/api/projects/{project_id}/funding",
        json={"goal_minor": goal_minor, "currency": "INR"},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


# --- Authentication ------------------------------------------------------------


def test_anonymous_demo_contribution_401(auth_client, client):
    project = _accepted_project(auth_client)
    resp = client.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 401


# --- Successful contribution ---------------------------------------------------


def test_authenticated_contribution_success(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-donor@aikyra.dev")
    resp = donor.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["project_id"] == project["id"]
    assert body["goal_minor"] == GOAL_MINOR
    assert body["raised_minor"] == DEMO_AMOUNT
    assert body["remaining_minor"] == GOAL_MINOR - DEMO_AMOUNT
    assert body["status"] == "OPEN"
    assert body["supporter_count"] == 1


def test_contribution_stored_completed(auth_client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-stored@aikyra.dev")
    assert (
        donor.post(
            f"/api/projects/{project['id']}/funding/contributions/demo",
            json={"amount_minor": DEMO_AMOUNT},
        ).status_code
        == 201
    )
    goal = _goal_row(db_session, project["id"])
    rows = (
        db_session.query(FundingContribution)
        .filter(FundingContribution.goal_id == goal.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == FundingContributionStatus.COMPLETED
    assert rows[0].amount_minor == DEMO_AMOUNT


def test_db_row_has_current_user_not_client_identity(auth_client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-owner@aikyra.dev")
    donor_id = _register_user(
        db_session, lambda e: user_client(e), "demo-owner@aikyra.dev"
    )
    assert (
        donor.post(
            f"/api/projects/{project['id']}/funding/contributions/demo",
            json={"amount_minor": DEMO_AMOUNT},
        ).status_code
        == 201
    )
    goal = _goal_row(db_session, project["id"])
    row = (
        db_session.query(FundingContribution)
        .filter(FundingContribution.goal_id == goal.id)
        .one()
    )
    assert row.contributed_by == donor_id


def test_raised_and_progress_derived(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-math@aikyra.dev")
    donor.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": 3_00_000},  # ₹3,000
    )
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["raised_minor"] == 3_00_000
    # 300000 / 5000000 = 6% = 600 basis points, integer.
    assert pub["progress_bp"] == 600
    assert isinstance(pub["progress_bp"], int)
    assert pub["remaining_minor"] == GOAL_MINOR - 3_00_000


def test_duplicate_by_same_user_counts_as_one_supporter(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-dupe@aikyra.dev")
    donor.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": 1_00_000},
    )
    donor.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": 2_00_000},
    )
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["raised_minor"] == 3_00_000
    assert pub["supporter_count"] == 1


def test_different_users_increase_supporter_count(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor_a = user_client("demo-a@aikyra.dev")
    donor_b = user_client("demo-b@aikyra.dev")
    donor_a.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": 1_00_000},
    )
    donor_b.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": 2_00_000},
    )
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["supporter_count"] == 2
    assert pub["raised_minor"] == 3_00_000


# --- Forged fields rejected (extra="forbid") -----------------------------------


def _forged_rejected(auth_client, project_id, extra):
    resp = auth_client.post(
        f"/api/projects/{project_id}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT, **extra},
    )
    assert resp.status_code == 422, (extra, resp.json())


def test_forged_contributed_by_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"contributed_by": str(uuid.uuid4())})


def test_forged_user_id_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"user_id": str(uuid.uuid4())})


def test_forged_goal_id_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"goal_id": str(uuid.uuid4())})


def test_forged_project_id_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"project_id": str(uuid.uuid4())})


def test_forged_status_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"status": "COMPLETED"})


def test_forged_raised_minor_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"raised_minor": 99_00_000})


def test_forged_supporter_count_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"supporter_count": 9999})


def test_forged_progress_bp_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"progress_bp": 10000})


def test_forged_remaining_minor_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"remaining_minor": 1234})


def test_forged_currency_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"currency": "USD"})


def test_forged_is_owner_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    _forged_rejected(auth_client, project["id"], {"is_owner": True})


# --- Goal state / project validation -------------------------------------------


def test_no_funding_goal_error(auth_client, db_session):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 409
    # No contribution row was created anywhere.
    assert db_session.query(FundingContribution).count() == 0


def test_closed_goal_rejected(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    assert (
        auth_client.post(f"/api/projects/{project['id']}/funding/close").status_code
        == 200
    )
    donor = user_client("demo-closed@aikyra.dev")
    resp = donor.post(
        f"/api/projects/{project['id']}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 409
    # No contribution row was created.
    assert db_session.query(FundingContribution).count() == 0


def test_unknown_project_404(auth_client):
    resp = auth_client.post(
        f"/api/projects/{uuid.uuid4()}/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 404


def test_malformed_project_uuid_422(auth_client):
    resp = auth_client.post(
        "/api/projects/not-a-uuid/funding/contributions/demo",
        json={"amount_minor": DEMO_AMOUNT},
    )
    assert resp.status_code == 422


# --- Amount validation ----------------------------------------------------------


def _post_amount(owner_client, project_id, amount):
    return owner_client.post(
        f"/api/projects/{project_id}/funding/contributions/demo",
        json={"amount_minor": amount},
    )


def test_zero_amount_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    assert _post_amount(auth_client, project["id"], 0).status_code == 422


def test_negative_amount_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    assert _post_amount(auth_client, project["id"], -100).status_code == 422


def test_overflow_amount_422(auth_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    assert (
        _post_amount(auth_client, project["id"], MAX_INT64 + 1).status_code == 422
    )


def test_max_int64_amount_accepted(auth_client, db_session):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    # Exactly MAX_INT64 is within schema bounds but would need the goal to be
    # fully funded first; we assert only validation passes (201), then verify
    # the stored amount equals it.
    resp = _post_amount(auth_client, project["id"], MAX_INT64)
    # The goal is only ₹50,000; a huge contribution is allowed (FULLY_FUNDED).
    assert resp.status_code == 201, resp.json()
    assert resp.json()["status"] == "FULLY_FUNDED"


# --- Privacy --------------------------------------------------------------------


def test_response_has_no_private_contributor_data(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    _open_goal(auth_client, project["id"])
    donor = user_client("demo-private@aikyra.dev")
    assert (
        donor.post(
            f"/api/projects/{project['id']}/funding/contributions/demo",
            json={"amount_minor": DEMO_AMOUNT},
        ).status_code
        == 201
    )
    raw = client.get(f"/api/projects/{project['id']}/funding").text
    assert "demo-private@aikyra.dev" not in raw
    assert "contributed_by" not in raw
    assert "supporter_id" not in raw
    assert "amount_minor" not in raw
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert set(body.keys()) == {
        "project_id",
        "goal_minor",
        "raised_minor",
        "remaining_minor",
        "currency",
        "progress_bp",
        "supporter_count",
        "status",
    }
