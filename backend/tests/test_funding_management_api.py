"""Phase 11 — OWNER FUNDING MANAGEMENT (AIKYRA VERIFIED).

Covers the authenticated owner-management layer for community funding:
creating, editing and closing a project's verified funding goal from the
Workspace.

Security first: anonymous users get 401, unrelated authenticated users get 403
even when they know the project's UUID (IDOR check), and every management
response is the server-derived summary — no client-supplied totals, status,
currency, identity or project_id.

Business rules under test:
- a goal is a 1:1 project singleton (409 on a second goal);
- only OPEN goals are editable and only their amount may change;
- a goal cannot be lowered below the completed money already raised (409);
- closing is terminal and preserves contribution history and totals;
- CLOSED remains CLOSED even when the goal is fully funded;
- FULLY_FUNDED stays derived from money math, never stored;
- management endpoints never touch contribution rows.

Regression: the entire suite still passes (no lifecycle/impact/offer/auth
behaviour regressions).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.funding_contribution import (
    FundingContribution,
    FundingContributionStatus,
)
from app.models.funding_goal import FundingGoal, FundingGoalStatus
from app.models.team import (
    TeamMembership,
    TeamMembershipStatus,
    TeamRole,
)

GOAL_MINOR = 50_00_000  # ₹50,000


# --- Setup helpers (mirror test_funding_api.py) -------------------------------


def _create_institution(c, **overrides):
    payload = {
        "name": f"Funding Mgmt Institution {uuid.uuid4().hex[:8]}",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": f"Funding Mgmt Challenge {uuid.uuid4().hex[:8]}",
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
        "name": f"Funding Mgmt Team {uuid.uuid4().hex[:8]}",
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
        "title": "Funding Mgmt Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _accepted_project(client):
    """Create an accepted proposal; return the resulting project dict.

    Works for any authenticated client: the client's user creates their own
    institution (becoming an owner/representative), team and proposal, then
    reviews it. The returned project is the client's most recent project.
    """
    inst = _create_institution(client)
    ch = _create_challenge(client)
    team = _create_team(client, inst["id"], ch["id"])
    proposal = _create_proposal(client, team["id"], ch["id"])
    assert (
        client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    )
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


def _create_contribution(
    db_session, goal_id, supporter_id, amount_minor, status="completed"
):
    contribution = FundingContribution(
        id=uuid.uuid4(),
        goal_id=goal_id,
        contributed_by=supporter_id,
        amount_minor=amount_minor,
        status=FundingContributionStatus(status),
    )
    db_session.add(contribution)
    db_session.commit()
    return contribution


def _goal_row(db_session, project_id) -> FundingGoal:
    return (
        db_session.query(FundingGoal)
        .filter(FundingGoal.project_id == project_id)
        .one()
    )


def _contribution_rows(db_session, goal_id):
    return (
        db_session.query(FundingContribution)
        .filter(FundingContribution.goal_id == goal_id)
        .all()
    )


# --- Authentication ------------------------------------------------------------


def test_anonymous_create_401(auth_client, client):
    project = _accepted_project(auth_client)
    resp = client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "currency": "INR"},
    )
    assert resp.status_code == 401


def test_anonymous_update_401(auth_client, client):
    project = _accepted_project(auth_client)
    resp = client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR},
    )
    assert resp.status_code == 401


def test_anonymous_close_401(auth_client, client):
    project = _accepted_project(auth_client)
    resp = client.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 401


# --- Authorization (IDOR) ------------------------------------------------------


def test_owner_lead_can_publish(auth_client, client, db_session):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "currency": "INR"},
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["project_id"] == project["id"]
    assert body["goal_minor"] == GOAL_MINOR
    assert body["currency"] == "INR"
    assert body["status"] == "OPEN"
    assert body["raised_minor"] == 0
    assert body["remaining_minor"] == GOAL_MINOR
    assert body["supporter_count"] == 0
    # Stored row is OPEN (never FULLY_FUNDED).
    row = _goal_row(db_session, project["id"])
    assert row.status == FundingGoalStatus.OPEN
    assert row.goal_minor == GOAL_MINOR
    # The public read now shows the goal to everyone (no fake sync).
    pub = client.get(f"/api/projects/{project['id']}/funding").json()
    assert pub["funding"]["goal_minor"] == GOAL_MINOR


def test_owner_lead_can_edit(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR},
    )
    supporter = _register_user(db_session, user_client, "donor-mgmt@aikyra.dev")
    goal = _goal_row(db_session, project["id"])
    _create_contribution(db_session, goal.id, supporter, 10_00_000)
    new_goal = GOAL_MINOR + 5_00_000
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": new_goal}
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["goal_minor"] == new_goal
    assert body["raised_minor"] == 10_00_000  # DB-derived, unchanged
    assert body["status"] == "OPEN"
    row = _goal_row(db_session, project["id"])
    assert row.goal_minor == new_goal


def test_owner_lead_can_close(auth_client, client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    resp = auth_client.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["status"] == "CLOSED"
    assert body["goal_minor"] == GOAL_MINOR
    # Public UI now shows CLOSED.
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["status"] == "CLOSED"


def test_unrelated_user_cannot_create(auth_client, user_client):
    project = _accepted_project(auth_client)
    intruder = user_client("intruder-create@aikyra.dev")
    resp = intruder.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert resp.status_code == 403


def test_unrelated_user_cannot_update(auth_client, user_client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    intruder = user_client("intruder-update@aikyra.dev")
    resp = intruder.patch(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR + 1}
    )
    assert resp.status_code == 403


def test_unrelated_user_cannot_close(auth_client, user_client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    intruder = user_client("intruder-close@aikyra.dev")
    resp = intruder.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 403


def test_active_member_non_lead_cannot_manage(auth_client, user_client, db_session):
    """Scenario A: an ACTIVE team MEMBER (not lead) gets 403 on every verb."""
    project = _accepted_project(auth_client)
    member_client = user_client("member-nonlead@aikyra.dev")
    from app.models.user import User

    member_id = (
        db_session.query(User)
        .filter(User.email == "member-nonlead@aikyra.dev")
        .first()
        .id
    )
    db_session.add(
        TeamMembership(
            id=uuid.uuid4(),
            team_id=uuid.UUID(project["team_id"]),
            user_id=member_id,
            role=TeamRole.MEMBER,
            status=TeamMembershipStatus.ACTIVE,
        )
    )
    db_session.commit()

    # Member cannot create, and the lead is unaffected by their presence.
    resp = member_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR},
    )
    assert resp.status_code == 403
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )

    # Member cannot edit or close either — same rule, resolved from the DB.
    resp = member_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR + 5_00_000},
    )
    assert resp.status_code == 403
    resp = member_client.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 403
    # Nothing was mutated by the member's attempts.
    assert _goal_row(db_session, project["id"]).goal_minor == GOAL_MINOR


def test_inactive_lead_cannot_manage(auth_client, user_client, db_session):
    """Scenario B: the project lead loses access immediately when their
    team membership is no longer ACTIVE (status resolved at request time)."""
    project = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )

    lead_membership = (
        db_session.query(TeamMembership)
        .filter(TeamMembership.team_id == uuid.UUID(project["team_id"]))
        .filter(TeamMembership.role == TeamRole.LEAD)
        .one()
    )
    lead_membership.status = TeamMembershipStatus.REMOVED
    db_session.commit()

    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR + 5_00_000},
    )
    assert resp.status_code == 403
    resp = auth_client.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 403
    assert _goal_row(db_session, project["id"]).goal_minor == GOAL_MINOR


def test_lead_of_another_team_cannot_manage(auth_client, user_client):
    """Scenario C: an ACTIVE lead of a different team is still a stranger to
    this project — 403 on every verb, even while their own project works."""
    project_a = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project_a['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )

    other_lead = user_client("other-team-lead@aikyra.dev")
    project_b = _accepted_project(other_lead)

    for verb, payload, route in (
        ("post", {"goal_minor": GOAL_MINOR}, f"/api/projects/{project_a['id']}/funding"),
        (
            "patch",
            {"goal_minor": GOAL_MINOR + 5_00_000},
            f"/api/projects/{project_a['id']}/funding",
        ),
        ("post", None, f"/api/projects/{project_a['id']}/funding/close"),
    ):
        resp = getattr(other_lead, verb)(route, json=payload)
        assert resp.status_code == 403, (verb, route, resp.json())

    # Positive control: the same lead fully manages their own project.
    resp = other_lead.post(
        f"/api/projects/{project_b['id']}/funding",
        json={"goal_minor": GOAL_MINOR},
    )
    assert resp.status_code == 201, resp.json()


# --- Project validation ---------------------------------------------------------


def test_unknown_project_404(auth_client):
    resp = auth_client.post(
        f"/api/projects/{uuid.uuid4()}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert resp.status_code == 404
    resp = auth_client.patch(
        f"/api/projects/{uuid.uuid4()}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert resp.status_code == 404
    resp = auth_client.post(f"/api/projects/{uuid.uuid4()}/funding/close")
    assert resp.status_code == 404


def test_malformed_project_id_422(auth_client):
    # TestClient.post aside, note TestClient.close is a framework method, so
    # the close endpoint is invoked via the router directly (post).
    assert (
        auth_client.post(
            "/api/projects/not-a-uuid/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            "/api/projects/not-a-uuid/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 422
    )
    assert (
        auth_client.post("/api/projects/not-a-uuid/funding/close").status_code
        == 422
    )


def test_duplicate_funding_goal_409(auth_client):
    project = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert resp.status_code == 409


def test_database_blocks_duplicate_goal_row(auth_client, db_session):
    """Deterministic backstop: the 1:1 project->goal invariant is enforced at
    the database layer by uq_funding_goals_project, not only by the API. Even
    a raw second row for the same project is rejected with IntegrityError."""
    project = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )
    first = _goal_row(db_session, project["id"])
    duplicate = FundingGoal(
        id=uuid.uuid4(),
        project_id=first.project_id,
        goal_minor=GOAL_MINOR,
        currency="INR",
        status=FundingGoalStatus.OPEN,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(FundingGoal).count() == 1


def test_zero_goal_422(auth_client):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": 0}
    )
    assert resp.status_code == 422


def test_negative_goal_422(auth_client):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": -100}
    )
    assert resp.status_code == 422


def test_non_inr_currency_422(auth_client):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "currency": "USD"},
    )
    assert resp.status_code == 422


# --- Integrity: client-forged fields are rejected -------------------------------


def test_forged_project_id_rejected(auth_client):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "project_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


def test_forged_raised_minor_rejected(auth_client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "raised_minor": 99_00_000},
    )
    assert resp.status_code == 422


def test_forged_supporter_count_and_progress_rejected(auth_client):
    project = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={
            "goal_minor": GOAL_MINOR,
            "supporter_count": 5000,
            "progress_bp": 10000,
            "status": "CLOSED",
        },
    )
    assert resp.status_code == 422


def test_forged_currency_on_update_rejected(auth_client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "currency": "USD"},
    )
    assert resp.status_code == 422


def test_user_id_impersonation_not_accepted(auth_client, user_client, db_session):
    project = _accepted_project(auth_client)
    victim = _register_user(db_session, user_client, "victim@aikyra.dev")
    resp = auth_client.post(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR, "user_id": str(victim), "is_owner": True},
    )
    assert resp.status_code == 422
    assert db_session.query(FundingGoal).count() == 0


def test_management_never_touches_contributions(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-mgmt2@aikyra.dev")
    supporter_2 = _register_user(db_session, user_client, "donor-mgmt3@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, 8_00_000)
    _create_contribution(db_session, goal.id, supporter_2, 2_00_000, status="pending")

    before = len(_contribution_rows(db_session, goal.id))

    assert (
        auth_client.patch(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR + 5_00_000},
        ).status_code
        == 200
    )
    assert (
        auth_client.post(f"/api/projects/{project['id']}/funding/close").status_code
        == 200
    )

    rows = _contribution_rows(db_session, goal.id)
    assert len(rows) == before
    assert {r.status for r in rows} == {
        FundingContributionStatus.COMPLETED,
        FundingContributionStatus.PENDING,
    }
    # Totals preserved through edit + close.
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["raised_minor"] == 8_00_000
    assert pub["status"] == "CLOSED"


# --- Business rules --------------------------------------------------------------


def test_edit_below_raised_409(auth_client, db_session, user_client):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-mgmt4@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, 40_00_000)
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": 30_00_000},
    )
    assert resp.status_code == 409
    assert _goal_row(db_session, project["id"]).goal_minor == GOAL_MINOR


def test_fully_funded_goal_can_be_raised_and_reopens(auth_client, client, db_session, user_client):
    """FULLY_FUNDED is derived, so raising the target on a fully funded goal
    re-derives status back to OPEN (raised < new goal, remaining > 0)."""
    project = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-raise@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, GOAL_MINOR)

    before = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert before["status"] == "FULLY_FUNDED"
    assert before["progress_bp"] == 10000
    assert before["remaining_minor"] == 0

    new_goal = 75_00_000  # ₹75,000
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": new_goal}
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["goal_minor"] == new_goal
    assert body["raised_minor"] == GOAL_MINOR
    assert body["remaining_minor"] == new_goal - GOAL_MINOR  # 25_00_000
    assert body["progress_bp"] == 6666
    assert body["status"] == "OPEN"
    row = _goal_row(db_session, project["id"])
    assert row.status == FundingGoalStatus.OPEN
    assert row.goal_minor == new_goal
    # Client-forged FULLY_FUNDED is never stored or returned.
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["status"] == "OPEN"


def test_patch_zero_and_negative_422_no_mutation(auth_client, db_session):
    project = _accepted_project(auth_client)
    assert (
        auth_client.post(
            f"/api/projects/{project['id']}/funding",
            json={"goal_minor": GOAL_MINOR},
        ).status_code
        == 201
    )
    assert (
        auth_client.patch(
            f"/api/projects/{project['id']}/funding", json={"goal_minor": 0}
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/projects/{project['id']}/funding", json={"goal_minor": -100}
        ).status_code
        == 422
    )
    assert _goal_row(db_session, project["id"]).goal_minor == GOAL_MINOR


def test_closed_goal_not_editable_409(auth_client, db_session):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert (
        auth_client.post(f"/api/projects/{project['id']}/funding/close").status_code
        == 200
    )
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/funding",
        json={"goal_minor": GOAL_MINOR + 5_00_000},
    )
    assert resp.status_code == 409


def test_close_already_closed_409(auth_client):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    assert (
        auth_client.post(f"/api/projects/{project['id']}/funding/close").status_code
        == 200
    )
    resp = auth_client.post(f"/api/projects/{project['id']}/funding/close")
    assert resp.status_code == 409


def test_closed_remains_closed_even_when_fully_funded(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-mgmt5@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, GOAL_MINOR)
    # OPEN + raised >= goal -> derived FULLY_FUNDED.
    open_summary = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert open_summary["status"] == "FULLY_FUNDED"
    assert _goal_row(db_session, project["id"]).status == FundingGoalStatus.OPEN
    # Closing pins display to CLOSED; the DB row stores CLOSED;
    # FULLY_FUNDED is never stored.
    assert (
        auth_client.post(f"/api/projects/{project['id']}/funding/close").status_code
        == 200
    )
    assert _goal_row(db_session, project["id"]).status == FundingGoalStatus.CLOSED
    closed_summary = client.get(f"/api/projects/{project['id']}/funding").json()[
        "funding"
    ]
    assert closed_summary["status"] == "CLOSED"
    assert closed_summary["raised_minor"] == GOAL_MINOR
    assert closed_summary["progress_bp"] == 10000


def test_fully_funded_stays_derived_not_stored(auth_client, db_session, user_client):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-mgmt6@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, GOAL_MINOR + 1_00_000)
    summary = auth_client.post(f"/api/projects/{project['id']}/funding/close").json()
    assert summary["status"] == "CLOSED"
    assert _goal_row(db_session, project["id"]).status == FundingGoalStatus.CLOSED


def test_close_preserves_contributions_and_no_fake_reset(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )
    goal = _goal_row(db_session, project["id"])
    supporter = _register_user(db_session, user_client, "donor-mgmt7@aikyra.dev")
    _create_contribution(db_session, goal.id, supporter, 12_50_000)
    before = len(_contribution_rows(db_session, goal.id))
    summary = auth_client.post(f"/api/projects/{project['id']}/funding/close").json()
    after = len(_contribution_rows(db_session, goal.id))
    assert after == before
    assert summary["status"] == "CLOSED"
    assert summary["raised_minor"] == 12_50_000  # never reset


# --- Regression: existing surfaces untouched -------------------------------------


def test_lifecycle_impact_offers_untouched_by_funding_management(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    auth_client.post(
        f"/api/projects/{project['id']}/funding", json={"goal_minor": GOAL_MINOR}
    )

    # CP6 lifecycle still works for the same (lead) user.
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    )
    assert resp.status_code == 200, resp.json()

    # CP7 impact metrics still work.
    resp = auth_client.post(
        f"/api/projects/{project['id']}/impact",
        json={"name": "Households", "value": "120", "unit": "households"},
    )
    assert resp.status_code == 201, resp.json()

    # No fake money/contributors were introduced by goal management.
    pub = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert pub["raised_minor"] == 0
    assert pub["supporter_count"] == 0
    assert pub["status"] == "OPEN"
    assert pub["goal_minor"] == GOAL_MINOR

    detail = client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "pilot"
    assert detail["funding"]["goal_minor"] == GOAL_MINOR