"""Phase 9 Checkpoint 9 — AIKYRA Impact Dashboard.

Covers the public read-only GET /api/dashboard: anonymous 200 with no auth
dependency, empty-database safety, DB-derived counts for every figure
(institutions, challenges + status grouping, teams, active people, proposal
submission/acceptance, project lifecycle, outcome reports, organizations,
support offers + type grouping, impact totals), the strict CORE_METRICS
allowlist (only unsigned-integer values may be summed; non-numeric and
unknown names are excluded from sums but kept verbatim on project cards),
bounded recent_implemented (max 5, created_at DESC, verbatim metrics), the
exact top-level key set, absence of any sensitive user/auth or
percentage/ratio fields, the "really live" proof (mutating the DB changes
the dashboard), and CP5/CP6/CP7 regression.
"""

import uuid
from datetime import datetime, timezone

from app.models.challenge import Challenge, ChallengeStatus
from app.models.institution import Institution, InstitutionStatus
from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.project import Project, ProjectStatus
from app.models.team import Team, TeamMembership, TeamMembershipStatus, TeamRole

TOP_LEVEL_KEYS = {"ecosystem", "pipeline", "support", "impact", "generated_at"}

SENSITIVE_SUBSTRINGS = (
    "email",
    "password",
    "hash",
    "jwt",
    "token",
    "reviewer",
    "credential",
)

RATIO_KEYS = ("_pct", "_percent", "_rate", "_ratio", "_avg", "percentage")


# --- Helpers (mirroring test_report_api.py patterns) --------------------------


def _create_institution(c, **overrides):
    payload = {
        "name": f"Dashboard Test Institution {uuid.uuid4().hex[:8]}",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": f"Dashboard Test Challenge {uuid.uuid4().hex[:8]}",
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
        "name": f"Dashboard Test Team {uuid.uuid4().hex[:8]}",
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
        "title": f"Dashboard Test Proposal {uuid.uuid4().hex[:8]}",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _accept_project(auth_client, team_id, challenge_id):
    proposal = _create_proposal(auth_client, team_id, challenge_id)
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


def _accepted_project(auth_client):
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    return _accept_project(auth_client, team["id"], ch["id"]), inst, team


def _advance_to_pilot(auth_client, pid):
    resp = auth_client.patch(
        f"/api/projects/{pid}/lifecycle", json={"status": "pilot"}
    )
    assert resp.status_code == 200, resp.json()


def _advance_to_implemented(auth_client, pid):
    """Idempotently drive a project to the terminal 'implemented' stage."""
    status = auth_client.get(f"/api/projects/{pid}").json()["status"]
    if status not in ("prototype", "pilot"):
        return
    if status == "prototype":
        _advance_to_pilot(auth_client, pid)
    resp = auth_client.patch(
        f"/api/projects/{pid}/lifecycle", json={"status": "implemented"}
    )
    assert resp.status_code == 200, resp.json()


def _create_metric(lead, pid, **overrides):
    payload = {
        "name": "Households reached",
        "value": "120",
        "unit": "households",
        "description": "Households benefiting from the pilot deployment.",
        **overrides,
    }
    resp = lead.post(f"/api/projects/{pid}/impact", json=payload)
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _create_report(auth_client, pid):
    resp = auth_client.post(
        f"/api/projects/{pid}/report",
        json={
            "summary": "The pilot delivered clean-energy access to four villages.",
            "results": "120 households connected; ~85 participants trained.",
            "lessons_learned": "Community buy-in drives adoption.",
            "next_steps": "Scale to two more districts.",
        },
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _create_offer(lead, pid, support_type, org_name):
    assert lead.post(
        "/api/organizations", json={"name": org_name}
    ).status_code == 201
    resp = lead.post(
        f"/api/projects/{pid}/offers",
        json={"support_type": support_type, "message": "Supporting the pilot."},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _dashboard(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _register_user(db_session, user_client, email, full_name="Dashboard Tester"):
    user_client(email)
    return _user_id(db_session, email)


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


def _create_institution_membership(db_session, user_id, institution_id, role, status="active"):
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


def _walk(obj, callback):
    """Recursively call callback for every (key, value) pair in a JSON body."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            callback(key, value)
            _walk(value, callback)
    elif isinstance(obj, list):
        for value in obj:
            _walk(value, callback)


# --- Basic reachability -------------------------------------------------------


def test_anonymous_get_200(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    assert resp.json()["generated_at"]


def test_exact_top_level_keys(client, auth_client):
    _accepted_project(auth_client)
    body = _dashboard(client)
    assert set(body.keys()) == TOP_LEVEL_KEYS


def test_empty_db_safe_structures(client, auth_client):
    # auth_client registration leaves no ecosystem rows behind.
    body = _dashboard(client)
    assert body["ecosystem"] == {
        "institutions": 0,
        "challenges_reported": 0,
        "teams_formed": 0,
        "people_engaged": 0,
    }
    assert body["pipeline"] == {
        "challenges_by_status": {
            "submitted": 0,
            "under_review": 0,
            "validated": 0,
            "rejected": 0,
        },
        "proposals_submitted": 0,
        "proposals_accepted": 0,
        "projects_by_status": {"prototype": 0, "pilot": 0, "implemented": 0},
        "projects_total": 0,
        "outcome_reports": 0,
    }
    assert body["support"] == {
        "organizations": 0,
        "offers_total": 0,
        "offers_by_type": {
            "funding": 0,
            "equipment": 0,
            "mentorship": 0,
            "pilot_support": 0,
        },
    }
    assert body["impact"] == {
        "metrics_total": 0,
        "projects_reporting": 0,
        "projects_with_report": 0,
        "reported_metrics": [],
        "recent_implemented": [],
    }
    # generated_at parses as an ISO timestamp.
    datetime.fromisoformat(body["generated_at"].replace("Z", "+00:00"))


# --- Ecosystem ----------------------------------------------------------------


def test_institution_count_active_only(client, auth_client, db_session):
    _create_institution(auth_client, name="Institution A")
    _create_institution(auth_client, name="Institution B")
    assert _dashboard(client)["ecosystem"]["institutions"] == 2

    inactive = _create_institution(auth_client, name="Institution C")
    inst = db_session.get(Institution, uuid.UUID(inactive["id"]))
    inst.status = InstitutionStatus.INACTIVE
    db_session.commit()
    assert _dashboard(client)["ecosystem"]["institutions"] == 2


def test_challenge_count(client, auth_client):
    _create_challenge(auth_client)
    _create_challenge(auth_client)
    assert _dashboard(client)["ecosystem"]["challenges_reported"] == 2


def test_challenge_status_grouping(client, auth_client, db_session):
    created = [_create_challenge(auth_client) for _ in range(4)]
    statuses = [
        ChallengeStatus.SUBMITTED,
        ChallengeStatus.UNDER_REVIEW,
        ChallengeStatus.VALIDATED,
        ChallengeStatus.REJECTED,
    ]
    for row, status in zip(created, statuses):
        challenge = db_session.get(Challenge, uuid.UUID(row["id"]))
        challenge.status = status
    db_session.commit()

    assert _dashboard(client)["pipeline"]["challenges_by_status"] == {
        "submitted": 1,
        "under_review": 1,
        "validated": 1,
        "rejected": 1,
    }


def test_team_count_excludes_archived(client, auth_client, db_session):
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team_a = _create_team(auth_client, inst["id"], ch["id"], name="Team A")
    _create_team(auth_client, inst["id"], ch["id"], name="Team B")
    assert _dashboard(client)["ecosystem"]["teams_formed"] == 2

    team = db_session.get(Team, uuid.UUID(team_a["id"]))
    team.status = "archived"
    db_session.commit()
    assert _dashboard(client)["ecosystem"]["teams_formed"] == 1


def test_active_people_excludes_invited_removed(client, auth_client, user_client, db_session):
    project, inst, team = _accepted_project(auth_client)
    # Team creator holds an active lead membership -> 1 person engaged.
    baseline = _dashboard(client)["ecosystem"]["people_engaged"]
    assert baseline == 1

    member_uid = _register_user(db_session, user_client, "member@aikyra.dev")
    invited_uid = _register_user(db_session, user_client, "invited@aikyra.dev")
    removed_uid = _register_user(db_session, user_client, "removed@aikyra.dev")

    _add_team_member(db_session, team["id"], member_uid)
    _add_team_member(db_session, team["id"], invited_uid, status="invited")
    _add_team_member(db_session, team["id"], removed_uid, status="removed")

    people = _dashboard(client)["ecosystem"]["people_engaged"]
    assert people == baseline + 1  # invited/removed excluded


# --- Pipeline -----------------------------------------------------------------


def test_proposal_submitted_count(client, auth_client):
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])

    draft = _create_proposal(auth_client, team["id"], ch["id"])
    # A draft has never been submitted and must not count.
    assert _dashboard(client)["pipeline"]["proposals_submitted"] == 0

    assert auth_client.post(f"/api/proposals/{draft['id']}/submit").status_code == 200
    assert _dashboard(client)["pipeline"]["proposals_submitted"] == 1


def test_proposal_accepted_count(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert _dashboard(client)["pipeline"]["proposals_submitted"] == 1
    assert _dashboard(client)["pipeline"]["proposals_accepted"] == 1
    assert _dashboard(client)["pipeline"]["projects_by_status"] == {
        "prototype": 1,
        "pilot": 0,
        "implemented": 0,
    }
    assert _dashboard(client)["pipeline"]["projects_total"] == 1


def test_project_lifecycle_counts_track_status(client, auth_client):
    project, _, _ = _accepted_project(auth_client)

    _advance_to_pilot(auth_client, project["id"])
    assert _dashboard(client)["pipeline"]["projects_by_status"] == {
        "prototype": 0,
        "pilot": 1,
        "implemented": 0,
    }

    _advance_to_implemented(auth_client, project["id"])
    assert _dashboard(client)["pipeline"]["projects_by_status"] == {
        "prototype": 0,
        "pilot": 0,
        "implemented": 1,
    }


def test_outcome_report_count(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])
    assert _dashboard(client)["pipeline"]["outcome_reports"] == 0
    _create_report(auth_client, project["id"])
    assert _dashboard(client)["pipeline"]["outcome_reports"] == 1


# --- Support ------------------------------------------------------------------


def test_organization_count(client, auth_client, user_client):
    assert _dashboard(client)["support"]["organizations"] == 0
    assert auth_client.post("/api/organizations", json={"name": "Org One"}).status_code == 201
    assert _dashboard(client)["support"]["organizations"] == 1


def test_support_offer_count_and_type_grouping(client, auth_client, user_client):
    project, _, _ = _accepted_project(auth_client)

    _create_offer(auth_client, project["id"], "funding", "FundCorp")
    second = user_client("second@aikyra.dev")
    _create_offer(second, project["id"], "mentorship", "MentorOrg")

    body = _dashboard(client)
    assert body["support"]["organizations"] == 2
    assert body["support"]["offers_total"] == 2
    assert body["support"]["offers_by_type"] == {
        "funding": 1,
        "equipment": 0,
        "mentorship": 1,
        "pilot_support": 0,
    }


# --- Impact -------------------------------------------------------------------


def test_impact_totals_and_report_project_count(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])

    _create_metric(auth_client, project["id"], name="Households reached", value="120")
    _create_metric(auth_client, project["id"], name="Villages covered", value="4", unit="villages")

    body = _dashboard(client)
    assert body["impact"]["metrics_total"] == 2
    assert body["impact"]["projects_reporting"] == 1
    assert body["impact"]["projects_with_report"] == 0

    _create_report(auth_client, project["id"])
    assert _dashboard(client)["impact"]["projects_with_report"] == 1


def test_safe_numeric_aggregation_across_projects(client, auth_client):
    project_a, _, _ = _accepted_project(auth_client)
    project_b, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project_a["id"])
    _advance_to_implemented(auth_client, project_b["id"])

    _create_metric(auth_client, project_a["id"], name="Households reached", value="120")
    _create_metric(auth_client, project_b["id"], name="Households reached", value="30")
    _create_metric(auth_client, project_b["id"], name="Pilot participants", value="85", unit="people")

    reported = _dashboard(client)["impact"]["reported_metrics"]
    by_name = {m["name"]: m for m in reported}
    assert by_name["Households reached"]["total"] == 150
    assert by_name["Pilot participants"]["total"] == 85
    assert len(reported) == 2


def test_non_numeric_values_excluded_from_sum_but_counted(client, auth_client, db_session):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])

    # " 85 " (surrounding whitespace) IS a valid unsigned integer and must
    # count — written straight to the DB because the API schema strips it.
    from app.models.project_impact_metric import ProjectImpactMetric

    db_session.add(
        ProjectImpactMetric(
            id=uuid.uuid4(),
            project_id=uuid.UUID(project["id"]),
            name="Pilot participants",
            value=" 85 ",
            unit="people",
            description=None,
        )
    )
    db_session.commit()

    # "~85%" is NOT summable: excluded from the rollup but still counted as a
    # stored metric and kept verbatim on the project card.
    metric = _create_metric(
        auth_client, project["id"], name="Pilot participants", value="~85%", unit="people"
    )

    body = _dashboard(client)
    assert body["impact"]["metrics_total"] == 2
    assert body["impact"]["projects_reporting"] == 1
    reported = body["impact"]["reported_metrics"]
    assert [m["name"] for m in reported] == ["Pilot participants"]
    assert reported[0]["total"] == 85

    # The verbatim card still shows the exact original strings.
    recent = body["impact"]["recent_implemented"][0]
    values = {m["value"] for m in recent["metrics"]}
    assert values == {" 85 ", "~85%"}
    assert metric["id"]


def test_unknown_metric_names_never_aggregated(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])

    _create_metric(auth_client, project["id"], name="Trees planted", value="500", unit="trees")

    body = _dashboard(client)
    assert body["impact"]["metrics_total"] == 1
    assert body["impact"]["reported_metrics"] == []
    # Verbatim evidence remains on the project card.
    recent = body["impact"]["recent_implemented"][0]
    assert recent["metrics"] == [
        {"name": "Trees planted", "value": "500", "unit": "trees"}
    ]


def test_deleting_metric_changes_totals(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])
    metric = _create_metric(auth_client, project["id"], name="Households reached", value="120")

    assert _dashboard(client)["impact"]["reported_metrics"] == [
        {"name": "Households reached", "unit": "households", "total": 120}
    ]

    resp = auth_client.delete(
        f"/api/projects/{project['id']}/impact/{metric['id']}"
    )
    assert resp.status_code == 204
    assert _dashboard(client)["impact"]["reported_metrics"] == []
    assert _dashboard(client)["impact"]["metrics_total"] == 0


def test_recent_implemented_limited_to_five(client, auth_client, db_session):
    created = []
    for i in range(7):
        project, _, _ = _accepted_project(auth_client)
        _advance_to_implemented(auth_client, project["id"])
        created.append(project)

    # Stagger created_at so ordering is fully deterministic (newest last).
    for i, project in enumerate(created):
        db_project = db_session.get(Project, uuid.UUID(project["id"]))
        db_project.created_at = datetime(
            2026, 1, i + 1, 12, 0, tzinfo=timezone.utc
        )
    db_session.commit()

    recent = _dashboard(client)["impact"]["recent_implemented"]
    assert len(recent) == 5
    # Newest first: the two oldest created projects are cut off.
    assert [p["title"] for p in recent] == [
        p["title"] for p in reversed(created[2:])
    ]
    assert all(p["status"] == "implemented" for p in recent)


def test_recent_project_metrics_verbatim(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])

    _create_metric(auth_client, project["id"], name="Households reached", value="120")
    _create_metric(auth_client, project["id"], name="Pilot participants", value="4x", unit="people")

    recent = _dashboard(client)["impact"]["recent_implemented"][0]
    assert recent["project_id"] == project["id"]
    assert recent["title"] == project["title"]
    assert recent["status"] == "implemented"
    assert recent["metrics"] == [
        {"name": "Households reached", "value": "120", "unit": "households"},
        {"name": "Pilot participants", "value": "4x", "unit": "people"},
    ]


# --- Security contract --------------------------------------------------------


def test_no_sensitive_fields(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    # Offers are only open before 'implemented', so offer first.
    _create_offer(auth_client, project["id"], "funding", "FundCorp")
    _advance_to_implemented(auth_client, project["id"])
    _create_metric(auth_client, project["id"], name="Households reached", value="120")
    _create_report(auth_client, project["id"])

    body = _dashboard(client)
    offenders = []

    def check(key, value):
        lowered = key.lower()
        if any(sub in lowered for sub in SENSITIVE_SUBSTRINGS):
            offenders.append(key)
        if isinstance(value, str) and "@" in value:
            offenders.append(f"{key}={value}")

    _walk(body, check)
    assert offenders == [], offenders
    # Explicit guard: the response must not contain any reviews dicts etc.
    assert "reviews" not in body and "proposals" not in body


def test_no_percentage_or_rate_fields(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _advance_to_implemented(auth_client, project["id"])
    _create_metric(auth_client, project["id"], name="Households reached", value="120")

    body = _dashboard(client)
    offenders = []

    def check(key, value):
        for marker in RATIO_KEYS:
            if marker in key.lower():
                offenders.append(key)

    _walk(body, check)
    assert offenders == [], offenders
    # No floats either — only whole counts.
    floats = []

    def check_number(key, value):
        if isinstance(value, float):
            floats.append(key)

    _walk(body, check_number)
    assert floats == [], floats


# --- The dashboard is really live (no hardcoding) -----------------------------


def test_lifecycle_change_moves_project_across_pipeline(client, auth_client):
    project, _, _ = _accepted_project(auth_client)

    assert _dashboard(client)["pipeline"]["projects_by_status"] == {
        "prototype": 1,
        "pilot": 0,
        "implemented": 0,
    }
    assert _dashboard(client)["impact"]["recent_implemented"] == []

    _advance_to_pilot(auth_client, project["id"])
    assert _dashboard(client)["pipeline"]["projects_by_status"]["pilot"] == 1

    _advance_to_implemented(auth_client, project["id"])
    body = _dashboard(client)
    assert body["pipeline"]["projects_by_status"] == {
        "prototype": 0,
        "pilot": 0,
        "implemented": 1,
    }
    assert [p["project_id"] for p in body["impact"]["recent_implemented"]] == [
        project["id"]
    ]


# --- Regression: CP5 offers / CP6 lifecycle / CP7 impact ----------------------


def test_regression_cp5_offers_still_present_on_dashboard(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _create_offer(auth_client, project["id"], "mentorship", "MentorHub")
    body = _dashboard(client)
    assert body["support"]["offers_total"] == 1
    assert body["support"]["offers_by_type"]["mentorship"] == 1
    # Project detail keeps offering offers — unaffected by the dashboard.
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["offers"][0]["support_type"] == "mentorship"


def test_regression_cp6_lifecycle_still_advances_normally(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert project["status"] == "prototype"
    _advance_to_implemented(auth_client, project["id"])
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "implemented"
    # Terminal: further transitions are still 409.
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 409


def test_regression_cp7_impact_editable_and_reflected(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"], name="Households reached", value="120")

    assert _dashboard(client)["impact"]["reported_metrics"] == [
        {"name": "Households reached", "unit": "households", "total": 120}
    ]

    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json={"name": "Households reached", "value": "999", "unit": "households"},
    )
    assert resp.status_code == 200, resp.json()
    assert _dashboard(client)["impact"]["reported_metrics"] == [
        {"name": "Households reached", "unit": "households", "total": 999}
    ]
    assert _dashboard(client)["impact"]["metrics_total"] == 1