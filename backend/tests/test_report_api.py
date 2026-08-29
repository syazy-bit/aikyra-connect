"""Phase 9 Checkpoint 8 — Project outcome report.

Covers: public read (anonymous and authenticated GET), the lead-only write
matrix on an *implemented* project (anonymous 401; active team lead
201/200/204; team member, non-lead institution owner/representative, an
organization manager, a platform reviewer and an unrelated user all 403), the
implemented-only lifecycle gate (prototype/pilot -> 409, implemented -> 201),
the 1:1 singleton rule (a second report on the same project -> 409), 404s
(unknown project for every verb, and a project that has no report yet), strict
request validation (missing/oversized/blank-after-strip summary; oversized
optional fields; forged ownership fields project_id/user_id/submitted_by/
team_id/report_id/created_at/updated_at rejected with 422 — never trusted),
detail embedding plus the list-item `has_report` flag, project-scoped reads
(no standalone report route: another project's report is unreachable), and
CP5/CP6/CP7 regression (offers remain closed and the lifecycle remains terminal
at implemented while impact stays editable alongside the report).
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
        "name": "Report Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": "Report Test Challenge",
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
        "name": "Report Test Team",
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
        "title": "Report Test Proposal",
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


def _second_project(auth_client):
    inst = _create_institution(
        auth_client, name="Second Report Test Institution"
    )
    ch = _create_challenge(auth_client, title="Second Report Test Challenge")
    team = _create_team(auth_client, inst["id"], ch["id"], name="Report Test Team B")
    return _accept_project(auth_client, team["id"], ch["id"]), inst


def _implement(auth_client, pid):
    assert (
        auth_client.patch(
            f"/api/projects/{pid}/lifecycle", json={"status": "pilot"}
        ).status_code
        == 200
    )
    resp = auth_client.patch(
        f"/api/projects/{pid}/lifecycle", json={"status": "implemented"}
    )
    assert resp.status_code == 200, resp.json()
    return resp.json()


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


def _register_user(db_session, user_client, email):
    user_client(email)
    return _user_id(db_session, email)


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _project_with_member_and_owner(db_session, auth_client, user_client):
    """Implemented project whose lead is auth_client, plus an active team
    member (member@aikyra.dev), a non-lead institution owner
    (owner@aikyra.dev) and a non-lead institution representative
    (representative@aikyra.dev). Returns (project dict, team dict, inst)."""
    project, inst, team = _accepted_project(auth_client)
    _implement(auth_client, project["id"])

    member_uid = _register_user(db_session, user_client, "member@aikyra.dev")
    _add_team_member(db_session, team["id"], member_uid)

    owner_uid = _register_user(db_session, user_client, "owner@aikyra.dev")
    _create_membership(db_session, owner_uid, inst["id"], "owner", "active")

    rep_uid = _register_user(db_session, user_client, "representative@aikyra.dev")
    _create_membership(db_session, rep_uid, inst["id"], "representative", "active")

    return project, team, inst


def _report_payload(**overrides):
    payload = {
        "summary": "The pilot deployed clean energy access in four villages.",
        "results": "120 households connected; ~85 participants trained.",
        "lessons_learned": "Community buy-in drives adoption.",
        "next_steps": "Scale to two more districts.",
    }
    payload.update(overrides)
    return payload


def _create_report(lead, pid, **overrides):
    resp = lead.post(f"/api/projects/{pid}/report", json=_report_payload(**overrides))
    assert resp.status_code == 201, resp.json()
    return resp.json()


# --- Public read -------------------------------------------------------------


def test_anonymous_get_200(auth_client, client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    resp = client.get(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["summary"].startswith("The pilot deployed")
    assert body["project_id"] == project["id"]
    assert body["id"]


def test_authenticated_get_200(auth_client, user_client, db_session):
    project, _, _ = _project_with_member_and_owner(db_session, auth_client, user_client)
    _create_report(auth_client, project["id"])
    resp = auth_client.get(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 200
    assert resp.json()["results"].startswith("120 households")


def test_get_404_when_no_report(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = client.get(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 404


def test_get_404_for_prototype_even_anonymous(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = client.get(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 404


# --- Detail embedding + list flag --------------------------------------------


def test_project_detail_report_none_before_create(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "implemented"
    assert detail["report"] is None


def test_project_detail_embeds_report_after_create(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    report = _create_report(auth_client, project["id"])
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["report"]["summary"] == report["summary"]
    assert detail["report"]["lessons_learned"] == report["lessons_learned"]


def test_list_item_has_report_flag(auth_client):
    project, _, _ = _accepted_project(auth_client)
    other, _ = _second_project(auth_client)

    def _flag(pid):
        item = next(
            i for i in auth_client.get("/api/projects").json()["items"] if i["id"] == pid
        )
        return item["has_report"]

    _implement(auth_client, project["id"])
    assert _flag(project["id"]) is False
    assert _flag(other["id"]) is False
    _create_report(auth_client, project["id"])
    assert _flag(project["id"]) is True
    assert _flag(other["id"]) is False


# --- Implemented-only lifecycle gate -----------------------------------------


def test_create_at_prototype_409(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 409


def test_create_at_pilot_409(auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 200
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 409


def test_create_at_implemented_201(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 201, resp.json()


# --- Write authorization -----------------------------------------------------


def test_team_lead_post_201(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["summary"] == _report_payload()["summary"]
    assert body["results"] == _report_payload()["results"]
    assert body["lessons_learned"] == _report_payload()["lessons_learned"]
    assert body["next_steps"] == _report_payload()["next_steps"]
    assert body["project_id"] == project["id"]
    assert body["id"]


def test_anonymous_post_401(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = client.post(f"/api/projects/{project['id']}/report", json=_report_payload())
    assert resp.status_code == 401


def test_team_member_post_403(db_session, auth_client, user_client):
    project, _, _ = _project_with_member_and_owner(db_session, auth_client, user_client)
    member = user_client("member@aikyra.dev")
    resp = member.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


def test_institution_owner_not_lead_post_403(db_session, auth_client, user_client):
    project, _, _ = _project_with_member_and_owner(db_session, auth_client, user_client)
    owner = user_client("owner@aikyra.dev")
    resp = owner.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


def test_institution_representative_post_403(db_session, auth_client, user_client):
    project, _, _ = _project_with_member_and_owner(db_session, auth_client, user_client)
    representative = user_client("representative@aikyra.dev")
    resp = representative.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


def test_org_manager_post_403(db_session, auth_client, user_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    manager = user_client("manager@aikyra.dev")
    assert manager.post(
        "/api/organizations", json={"name": "Report Test Org"}
    ).status_code == 201
    resp = manager.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


def test_unrelated_user_post_403(db_session, auth_client, user_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _register_user(db_session, user_client, "stranger@aikyra.dev")
    stranger = user_client("stranger@aikyra.dev")
    resp = stranger.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


def test_platform_reviewer_post_403(auth_client, reviewer_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = reviewer_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 403


# --- Singleton: no duplicate reports -----------------------------------------


def test_second_report_409(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 409
    # The original report is untouched.
    assert auth_client.get(
        f"/api/projects/{project['id']}/report"
    ).json()["summary"] == _report_payload()["summary"]


# --- Lead mutations ----------------------------------------------------------


def test_lead_patch_200(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(summary="Updated final summary."),
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["summary"] == "Updated final summary."


def test_lead_delete_204(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    resp = auth_client.delete(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 204
    assert resp.content == b""
    assert auth_client.get(f"/api/projects/{project['id']}/report").status_code == 404


def test_report_can_be_recreated_after_delete(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"], summary="First summary.")
    assert auth_client.delete(f"/api/projects/{project['id']}/report").status_code == 204
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(summary="Second summary."),
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["summary"] == "Second summary."


def test_patch_when_no_report_404(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    )
    assert resp.status_code == 404


def test_delete_when_no_report_404(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.delete(f"/api/projects/{project['id']}/report")
    assert resp.status_code == 404


# --- Cross-project security (no standalone report-ID route) -------------------


def test_cross_project_patch_404(auth_client):
    project_a, _, _ = _accepted_project(auth_client)
    project_b, _ = _second_project(auth_client)
    _implement(auth_client, project_a["id"])
    _create_report(auth_client, project_a["id"], summary="Project A summary.")
    resp = auth_client.patch(
        f"/api/projects/{project_b['id']}/report",
        json=_report_payload(summary="Hijacked summary."),
    )
    assert resp.status_code == 404
    # Project A's report is untouched.
    assert auth_client.get(
        f"/api/projects/{project_a['id']}/report"
    ).json()["summary"] == "Project A summary."


def test_cross_project_delete_404(auth_client):
    project_a, _, _ = _accepted_project(auth_client)
    project_b, _ = _second_project(auth_client)
    _implement(auth_client, project_a["id"])
    _create_report(auth_client, project_a["id"])
    resp = auth_client.delete(f"/api/projects/{project_b['id']}/report")
    assert resp.status_code == 404
    assert auth_client.get(f"/api/projects/{project_a['id']}/report").status_code == 200


# --- 404s --------------------------------------------------------------------


def test_unknown_project_get_404(client):
    resp = client.get(f"/api/projects/{uuid.uuid4()}/report")
    assert resp.status_code == 404


def test_unknown_project_post_404(auth_client):
    resp = auth_client.post(
        f"/api/projects/{uuid.uuid4()}/report", json=_report_payload()
    )
    assert resp.status_code == 404


def test_unknown_project_patch_404(auth_client):
    resp = auth_client.patch(
        f"/api/projects/{uuid.uuid4()}/report", json=_report_payload()
    )
    assert resp.status_code == 404


def test_unknown_project_delete_404(auth_client):
    resp = auth_client.delete(f"/api/projects/{uuid.uuid4()}/report")
    assert resp.status_code == 404


# --- Validation --------------------------------------------------------------

REPORT_MAX = 20_000


def test_missing_summary_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    payload = {k: v for k, v in _report_payload().items() if k != "summary"}
    resp = auth_client.post(f"/api/projects/{project['id']}/report", json=payload)
    assert resp.status_code == 422


def test_blank_summary_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(summary=" \t "),
    )
    assert resp.status_code == 422


def test_oversized_summary_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(summary="A" * (REPORT_MAX + 1)),
    )
    assert resp.status_code == 422


def test_oversized_results_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(results="A" * (REPORT_MAX + 1)),
    )
    assert resp.status_code == 422


def test_oversized_lessons_learned_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(lessons_learned="A" * (REPORT_MAX + 1)),
    )
    assert resp.status_code == 422


def test_oversized_next_steps_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    resp = auth_client.post(
        f"/api/projects/{project['id']}/report",
        json=_report_payload(next_steps="A" * (REPORT_MAX + 1)),
    )
    assert resp.status_code == 422


def test_strip_and_blank_optionals_become_none(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    report = _create_report(
        auth_client,
        project["id"],
        results="   ",
        lessons_learned="\t",
        next_steps=None,
    )
    assert report["results"] is None
    assert report["lessons_learned"] is None
    assert report["next_steps"] is None


def test_max_length_summary_accepted(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    report = _create_report(auth_client, project["id"], summary="A" * REPORT_MAX)
    assert len(report["summary"]) == REPORT_MAX


# --- Forged / mass-assignment fields -----------------------------------------


def test_forged_ownership_fields_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    for field, value in [
        ("project_id", str(uuid.uuid4())),
        ("team_id", str(uuid.uuid4())),
        ("user_id", str(uuid.uuid4())),
        ("submitted_by", str(uuid.uuid4())),
        ("created_by", str(uuid.uuid4())),
        ("report_id", str(uuid.uuid4())),
        ("id", str(uuid.uuid4())),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ]:
        resp = auth_client.post(
            f"/api/projects/{project['id']}/report",
            json=_report_payload(**{field: value}),
        )
        assert resp.status_code == 422, (field, resp.json())


def test_forged_fields_rejected_on_patch(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    payload = _report_payload(summary="Forged edit.")
    payload.update({"project_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4())})
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/report", json=payload
    )
    assert resp.status_code == 422
    assert auth_client.get(
        f"/api/projects/{project['id']}/report"
    ).json()["summary"] == _report_payload()["summary"]


# --- Regression: CP5 offers + CP6 lifecycle + CP7 impact ---------------------


def test_report_requires_implemented_lifecycle(auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert project["status"] == "prototype"
    assert auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    ).status_code == 409

    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 200
    assert auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    ).status_code == 409

    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "implemented"}
    ).status_code == 200
    assert auth_client.post(
        f"/api/projects/{project['id']}/report", json=_report_payload()
    ).status_code == 201


def test_lifecycle_still_terminal_after_report(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "implemented"
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 409
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "implemented"}
    ).status_code == 409


def test_offers_remain_closed_while_report_written(auth_client):
    project, _, _ = _accepted_project(auth_client)
    auth_client.post("/api/organizations", json={"name": "Report FundCorp"})
    assert auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "funding", "message": "Early support."},
    ).status_code == 201
    _implement(auth_client, project["id"])

    assert auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "equipment", "message": "Too late."},
    ).status_code == 409

    report = _create_report(auth_client, project["id"])
    assert report["summary"].startswith("The pilot deployed")
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert [o["support_type"] for o in detail["offers"]] == ["funding"]


def test_impact_still_editable_at_implemented_with_report(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = auth_client.post(
        f"/api/projects/{project['id']}/impact",
        json={
            "name": "Households reached",
            "value": "120",
            "unit": "households",
            "description": "Households benefiting from the pilot deployment.",
        },
    )
    assert metric.status_code == 201, metric.json()
    _implement(auth_client, project["id"])
    _create_report(auth_client, project["id"])

    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric.json()['id']}",
        json={
            "name": "Households reached",
            "value": "150",
            "unit": "households",
            "description": "Households benefiting from the pilot deployment.",
        },
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["value"] == "150"

    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["report"] is not None
    assert detail["impact"][0]["value"] == "150"