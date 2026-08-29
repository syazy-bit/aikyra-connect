"""Phase 10 — AIKYRA VERIFIED COMMUNITY FUNDING.

Covers: anonymous public read of a project's verified funding goal; the safe
empty response when a project has no campaign; server-derived aggregation of
COMPLETED contributions only (PENDING/FAILED/REFUNDED money never counts,
integer minor units, no floats); supporter-count semantics (distinct supporters
with at least one completed contribution); server-side progress math (basis
points, capped at 10000, never a client-supplied percentage); the derived
OPEN / FULLY_FUNDED / CLOSED status (FULLY_FUNDED never stored); 404 for
unknown projects; DB-level rejection of zero/negative amounts; privacy
(no contribution, amount, supporter account or email ever returned); the
absence of write endpoints (a project's funding is read-only in this slice);
embedded summaries on the project list and detail; and regression that the
funding surface never disturbs the CP6 lifecycle / CP7 impact surfaces.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.funding_contribution import (
    FundingContribution,
    FundingContributionStatus,
)
from app.models.funding_goal import FundingGoal, FundingGoalStatus

# Example goal from the brief: ₹40,000 goal with ₹12,000 raised.
GOAL_MINOR = 40_00_000  # ₹40,000
RAISED_MINOR = 12_00_000  # ₹12,000


def _create_institution(c, **overrides):
    payload = {
        "name": "Funding Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": "Funding Test Challenge",
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
        "name": "Funding Test Team",
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
        "title": "Funding Test Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _accepted_project(auth_client):
    """Create an accepted proposal and return the resulting project dict."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review",
            json={"action": "start_review"},
        ).status_code
        == 200
    )
    resp = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert resp.status_code == 200, resp.json()
    return auth_client.get("/api/projects").json()["items"][0]


def _register_user(db_session, user_client, email):
    user_client(email)
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _create_goal(db_session, project_id, goal_minor=GOAL_MINOR, **overrides):
    goal = FundingGoal(
        id=uuid.uuid4(),
        project_id=project_id,
        goal_minor=goal_minor,
        status=FundingGoalStatus.OPEN,
        **overrides,
    )
    db_session.add(goal)
    db_session.commit()
    return goal


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


def _goal_and_supporter(db_session, auth_client, user_client, project_id):
    goal = _create_goal(db_session, project_id)
    supporter_id = _register_user(db_session, user_client, "donor@aikyra.dev")
    return goal, supporter_id


# --- Public read --------------------------------------------------------------


def test_get_200_anonymous(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, RAISED_MINOR)
    resp = client.get(f"/api/projects/{project['id']}/funding")
    assert resp.status_code == 200, resp.json()


def test_no_campaign_safe_empty(auth_client, client):
    project = _accepted_project(auth_client)
    resp = client.get(f"/api/projects/{project['id']}/funding")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["project_id"] == project["id"]
    assert body["funding"] is None


def test_goal_shape(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, _ = _goal_and_supporter(db_session, auth_client, user_client, project["id"])
    body = client.get(f"/api/projects/{project['id']}/funding").json()
    assert body["funding"]["goal_minor"] == GOAL_MINOR
    assert body["funding"]["currency"] == "INR"
    assert body["funding"]["status"] == "OPEN"
    assert body["funding"]["raised_minor"] == 0
    assert body["funding"]["remaining_minor"] == GOAL_MINOR
    assert body["funding"]["progress_bp"] == 0
    assert body["funding"]["supporter_count"] == 0


# --- Aggregation semantics ----------------------------------------------------


def test_completed_contributions_aggregated(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 3_00_000)
    _create_contribution(db_session, goal.id, supporter_id, 1_25_000)
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 4_25_000
    assert body["supporter_count"] == 1


def test_pending_excluded(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 5_00_000, status="pending")
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 0
    assert body["supporter_count"] == 0


def test_failed_excluded(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 5_00_000, status="failed")
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 0
    assert body["supporter_count"] == 0


def test_refunded_excluded(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 5_00_000, status="refunded")
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 0
    assert body["supporter_count"] == 0


def test_mixed_statuses_count_only_completed(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 2_00_000)
    _create_contribution(db_session, goal.id, supporter_id, 1_00_000, status="pending")
    _create_contribution(db_session, goal.id, supporter_id, 1_00_000, status="failed")
    _create_contribution(db_session, goal.id, supporter_id, 1_00_000, status="refunded")
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 2_00_000
    assert body["supporter_count"] == 1


def test_supporter_count_is_distinct(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    donor_2 = _register_user(db_session, user_client, "donor2@aikyra.dev")
    donor_3 = _register_user(db_session, user_client, "donor3@aikyra.dev")
    # donor_3 is pending only — must not count as a supporter.
    _create_contribution(db_session, goal.id, supporter_id, 1_00_000)
    _create_contribution(db_session, goal.id, supporter_id, 50_000)
    _create_contribution(db_session, goal.id, donor_2, 2_00_000)
    _create_contribution(db_session, goal.id, donor_3, 3_00_000, status="pending")
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["raised_minor"] == 3_50_000
    assert body["supporter_count"] == 2


def test_progress_bp_server_math(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 3_00_000)
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    # 300000 / 4000000 = 7.5% = 750 basis points — integer, not a float.
    assert body["progress_bp"] == 750
    assert isinstance(body["progress_bp"], int)
    assert body["remaining_minor"] == GOAL_MINOR - 3_00_000


# --- Status derivation --------------------------------------------------------


def test_fully_funded_derived(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, GOAL_MINOR)
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["status"] == "FULLY_FUNDED"
    assert body["progress_bp"] == 10000
    assert body["remaining_minor"] == 0


def test_overfunded_caps_progress_at_full(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, GOAL_MINOR + 5_00_000)
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["status"] == "FULLY_FUNDED"
    assert body["raised_minor"] == GOAL_MINOR + 5_00_000
    assert body["remaining_minor"] == 0
    assert body["progress_bp"] == 10000


def test_closed_under_goal(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 10_00_000)
    goal.status = FundingGoalStatus.CLOSED
    db_session.commit()
    body = client.get(f"/api/projects/{project['id']}/funding").json()["funding"]
    assert body["status"] == "CLOSED"
    assert body["raised_minor"] == 10_00_000


# --- 404s and method guard ----------------------------------------------------


def test_unknown_project_404(client):
    resp = client.get(f"/api/projects/{uuid.uuid4()}/funding")
    assert resp.status_code == 404


def test_invalid_project_id_422(client):
    resp = client.get("/api/projects/not-a-uuid/funding")
    assert resp.status_code == 422


def test_no_write_endpoints_405(auth_client, client):
    project = _accepted_project(auth_client)
    assert client.post(f"/api/projects/{project['id']}/funding", json={}).status_code == 405
    assert client.put(f"/api/projects/{project['id']}/funding", json={}).status_code == 405
    assert client.patch(f"/api/projects/{project['id']}/funding", json={}).status_code == 405
    assert client.delete(f"/api/projects/{project['id']}/funding").status_code == 405


def test_query_params_ignored(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 4_25_000)
    # Forged totals/percentages in the query string are ignored.
    resp = client.get(
        f"/api/projects/{project['id']}/funding",
        params={"raised_minor": 99, "progress_bp": 9999, "supporter_count": 999},
    )
    assert resp.status_code == 200
    body = resp.json()["funding"]
    assert body["raised_minor"] == 4_25_000
    assert body["supporter_count"] == 1
    assert body["progress_bp"] == 1062
    assert isinstance(body["progress_bp"], int)


# --- Privacy ------------------------------------------------------------------


def test_no_private_data_in_response(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 4_25_000)
    raw = client.get(f"/api/projects/{project['id']}/funding").text
    assert "donor@aikyra.dev" not in raw
    assert "supporter_id" not in raw
    assert "contributed_by" not in raw
    assert "amount_minor" not in raw
    assert "email" not in raw
    assert "password" not in raw
    assert "hashed_password" not in raw
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


# --- Embedding on list and detail ---------------------------------------------


def test_list_item_funding_null_without_goal(auth_client, client):
    project = _accepted_project(auth_client)
    item = next(
        i for i in client.get("/api/projects").json()["items"] if i["id"] == project["id"]
    )
    assert item["funding"] is None


def test_list_item_embeds_funding(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 4_25_000)
    item = next(
        i for i in client.get("/api/projects").json()["items"] if i["id"] == project["id"]
    )
    assert item["funding"] is not None
    assert item["funding"]["raised_minor"] == 4_25_000
    assert item["funding"]["status"] == "OPEN"


def test_detail_embeds_funding(auth_client, client, db_session, user_client):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 4_25_000)
    detail = client.get(f"/api/projects/{project['id']}").json()
    assert detail["funding"] is not None
    assert detail["funding"]["project_id"] == project["id"]
    assert detail["funding"]["raised_minor"] == 4_25_000


def test_detail_funding_null_without_goal(auth_client, client):
    project = _accepted_project(auth_client)
    detail = client.get(f"/api/projects/{project['id']}").json()
    assert detail["funding"] is None


# --- DB-level integrity guard -------------------------------------------------


def test_zero_and_negative_amounts_rejected(db_session, auth_client):
    project = _accepted_project(auth_client)
    goal = _create_goal(db_session, project["id"])
    from app.models.user import User

    supporter_id = db_session.query(User).first().id
    for bad_amount in (0, -1, -999_99):
        with pytest.raises(IntegrityError):
            _create_contribution(db_session, goal.id, supporter_id, bad_amount)
        db_session.rollback()


def test_non_iso_currency_rejected(db_session, auth_client):
    project = _accepted_project(auth_client)
    # A 4-char code is rejected by the VARCHAR(3) column before any CHECK rule.
    with pytest.raises(SQLAlchemyError) as excinfo:
        _create_goal(db_session, project["id"], currency="USD$")
    db_session.rollback()
    assert "value too long" in str(excinfo.value)
    # Any 3-char non-INR code violates the allowlist rule.
    with pytest.raises(IntegrityError) as excinfo2:
        _create_goal(db_session, project["id"], currency="XYZ")
    db_session.rollback()
    assert "ck_funding_goals_currency_inr" in str(excinfo2.value)


def test_zero_goal_rejected(db_session, auth_client):
    project = _accepted_project(auth_client)
    with pytest.raises(IntegrityError):
        _create_goal(db_session, project["id"], goal_minor=0)
    db_session.rollback()


# --- Regression: existing surfaces untouched ----------------------------------


def test_lifecycle_impact_untouched_by_funding(
    auth_client, client, db_session, user_client
):
    project = _accepted_project(auth_client)
    goal, supporter_id = _goal_and_supporter(
        db_session, auth_client, user_client, project["id"]
    )
    _create_contribution(db_session, goal.id, supporter_id, 4_25_000)
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    )
    assert resp.status_code == 200, resp.json()
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "implemented"}
    )
    assert resp.status_code == 200, resp.json()
    metric = auth_client.post(
        f"/api/projects/{project['id']}/impact",
        json={"name": "Households", "value": "120", "unit": "households"},
    )
    assert metric.status_code == 201, metric.json()
    detail = client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "implemented"
    assert detail["impact"][0]["value"] == "120"
    assert detail["funding"]["raised_minor"] == 4_25_000