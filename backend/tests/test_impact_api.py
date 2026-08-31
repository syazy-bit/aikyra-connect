"""Phase 8 Checkpoint 7 — Project impact metrics.

Covers: public read (anonymous and authenticated GET), the lead-only write
matrix (anonymous 401; active team lead 201/200/204; team member, institution
admin who is not a lead, unrelated user and platform reviewer all 403), 404s
(unknown project, unknown metric, and a metric of another project addressed
through a foreign project URL — cross-project modification is impossible),
strict request validation (missing/oversized/blank-after-strip fields, and
forged ownership fields project_id/user_id/team_id/created_at/updated_at/
created_by rejected with 422 never trusted), detail embedding + created_at ASC
ordering, impact usability across the whole prototype -> pilot -> implemented
lifecycle, and CP5/CP6 regression (support offers still open through pilot and
rejected once implemented while impact stays editable).
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
        "name": "Impact Test Institution",
        "institution_type": "university",
        "location": "Test Location",
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_challenge(c, **overrides):
    payload = {
        "title": "Impact Test Challenge",
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
        "name": "Impact Test Team",
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
        "title": "Impact Test Proposal",
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
        auth_client, name="Second Impact Test Institution"
    )
    ch = _create_challenge(auth_client, title="Second Impact Test Challenge")
    team = _create_team(auth_client, inst["id"], ch["id"], name="Impact Test Team B")
    return _accept_project(auth_client, team["id"], ch["id"]), inst


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
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _project_with_member_and_admin(db_session, auth_client, user_client):
    """Accepted project whose lead is auth_client, plus an active team member
    (member@aikyra.dev) and an institution admin (admin@aikyra.dev) who is not
    on the team. Returns (project dict, team dict, institution dict)."""
    project, inst, team = _accepted_project(auth_client)

    member_uid = _register_user(db_session, user_client, "member@aikyra.dev")
    _add_team_member(db_session, team["id"], member_uid)

    _register_user(db_session, user_client, "admin@aikyra.dev")
    admin_uid = _user_id(db_session, "admin@aikyra.dev")
    _create_membership(db_session, admin_uid, inst["id"], "institution_admin", "active")

    return project, team, inst


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _metric_payload(**overrides):
    payload = {
        "name": "Households reached",
        "value": "120",
        "unit": "households",
        "description": "Households benefiting from the pilot deployment.",
    }
    payload.update(overrides)
    return payload


def _create_metric(lead, pid, **overrides):
    resp = lead.post(f"/api/projects/{pid}/impact", json=_metric_payload(**overrides))
    assert resp.status_code == 201, resp.json()
    return resp.json()


# --- Public read -------------------------------------------------------------


def test_anonymous_get_200(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    _create_metric(auth_client, project["id"])
    resp = client.get(f"/api/projects/{project['id']}/impact")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_authenticated_get_200(auth_client, user_client, db_session):
    project, _, _ = _project_with_member_and_admin(db_session, auth_client, user_client)
    _create_metric(auth_client, project["id"])
    resp = auth_client.get(f"/api/projects/{project['id']}/impact")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_empty_when_no_metrics(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = client.get(f"/api/projects/{project['id']}/impact")
    assert resp.status_code == 200
    assert resp.json() == []


# --- Write authorization -----------------------------------------------------


def test_team_lead_post_201(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = auth_client.post(
        f"/api/projects/{project['id']}/impact", json=_metric_payload()
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["name"] == "Households reached"
    assert body["value"] == "120"
    assert body["unit"] == "households"
    assert body["description"] == "Households benefiting from the pilot deployment."
    assert body["project_id"] == project["id"]
    assert body["id"]


def test_anonymous_post_401(client, auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = client.post(f"/api/projects/{project['id']}/impact", json=_metric_payload())
    assert resp.status_code == 401


def test_team_member_post_403(db_session, auth_client, user_client):
    project, _, _ = _project_with_member_and_admin(db_session, auth_client, user_client)
    member = user_client("member@aikyra.dev")
    resp = member.post(f"/api/projects/{project['id']}/impact", json=_metric_payload())
    assert resp.status_code == 403


def test_institution_admin_not_lead_post_403(db_session, auth_client, user_client):
    project, _, _ = _project_with_member_and_admin(db_session, auth_client, user_client)
    admin = user_client("admin@aikyra.dev")
    resp = admin.post(f"/api/projects/{project['id']}/impact", json=_metric_payload())
    assert resp.status_code == 403


def test_unrelated_user_post_403(db_session, auth_client, user_client):
    project, _, _ = _accepted_project(auth_client)
    _register_user(db_session, user_client, "stranger@aikyra.dev")
    stranger = user_client("stranger@aikyra.dev")
    resp = stranger.post(f"/api/projects/{project['id']}/impact", json=_metric_payload())
    assert resp.status_code == 403


def test_platform_reviewer_post_403(auth_client, reviewer_client):
    project, _, _ = _accepted_project(auth_client)
    resp = reviewer_client.post(
        f"/api/projects/{project['id']}/impact", json=_metric_payload()
    )
    assert resp.status_code == 403


# --- Lead mutations ----------------------------------------------------------


def test_lead_patch_200(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"])
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json=_metric_payload(value="125", name="Households reached"),
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["value"] == "125"
    assert resp.json()["project_id"] == project["id"]


def test_lead_delete_204(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"])
    resp = auth_client.delete(f"/api/projects/{project['id']}/impact/{metric['id']}")
    assert resp.status_code == 204
    assert resp.content == b""


def test_deleted_metric_no_longer_appears(auth_client):
    project, _, _ = _accepted_project(auth_client)
    kept = _create_metric(auth_client, project["id"], name="Kept metric", value="1")
    deleted = _create_metric(auth_client, project["id"], name="Deleted metric", value="2")
    assert auth_client.delete(
        f"/api/projects/{project['id']}/impact/{deleted['id']}"
    ).status_code == 204

    list_resp = auth_client.get(f"/api/projects/{project['id']}/impact")
    assert list_resp.status_code == 200
    names = [m["name"] for m in list_resp.json()]
    assert names == ["Kept metric"]

    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert [m["name"] for m in detail["impact"]] == ["Kept metric"]
    assert kept["id"] in [m["id"] for m in detail["impact"]]


# --- Cross-project security --------------------------------------------------


def test_cross_project_patch_404(auth_client):
    project_a, _, _ = _accepted_project(auth_client)
    project_b, _ = _second_project(auth_client)
    metric_a = _create_metric(auth_client, project_a["id"])
    resp = auth_client.patch(
        f"/api/projects/{project_b['id']}/impact/{metric_a['id']}",
        json=_metric_payload(value="999"),
    )
    assert resp.status_code == 404


def test_cross_project_delete_404(auth_client):
    project_a, _, _ = _accepted_project(auth_client)
    project_b, _ = _second_project(auth_client)
    metric_a = _create_metric(auth_client, project_a["id"])
    resp = auth_client.delete(f"/api/projects/{project_b['id']}/impact/{metric_a['id']}")
    assert resp.status_code == 404
    # The metric itself is untouched.
    assert auth_client.get(f"/api/projects/{project_a['id']}/impact").json()[0]["name"] == (
        "Households reached"
    )


# --- 404s --------------------------------------------------------------------


def test_unknown_project_get_404(client, auth_client):
    resp = client.get(f"/api/projects/{uuid.uuid4()}/impact")
    assert resp.status_code == 404


def test_unknown_project_post_404(auth_client):
    resp = auth_client.post(
        f"/api/projects/{uuid.uuid4()}/impact", json=_metric_payload()
    )
    assert resp.status_code == 404


def test_unknown_metric_patch_404(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{uuid.uuid4()}",
        json=_metric_payload(value="999"),
    )
    assert resp.status_code == 404


def test_unknown_metric_delete_404(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = auth_client.delete(f"/api/projects/{project['id']}/impact/{uuid.uuid4()}")
    assert resp.status_code == 404


# --- Validation --------------------------------------------------------------


def _post_invalid(auth_client, pid, payload):
    return auth_client.post(f"/api/projects/{pid}/impact", json=payload)


def test_missing_name_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(
        auth_client,
        project["id"],
        {k: v for k, v in _metric_payload().items() if k != "name"},
    )
    assert resp.status_code == 422


def test_missing_value_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(
        auth_client,
        project["id"],
        {k: v for k, v in _metric_payload().items() if k != "value"},
    )
    assert resp.status_code == 422


def test_oversized_name_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(name="A" * 301))
    assert resp.status_code == 422


def test_oversized_value_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(value="A" * 101))
    assert resp.status_code == 422


def test_oversized_unit_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(unit="A" * 51))
    assert resp.status_code == 422


def test_oversized_description_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(description="A" * 501))
    assert resp.status_code == 422


def test_blank_after_strip_name_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(name="   "))
    assert resp.status_code == 422


def test_blank_after_strip_value_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    resp = _post_invalid(auth_client, project["id"], _metric_payload(value=" \t "))
    assert resp.status_code == 422


def test_strip_and_blank_optional_become_none(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(
        auth_client, project["id"], unit="  ", description="   "
    )
    assert metric["unit"] is None
    assert metric["description"] is None


# --- Forged / mass-assignment fields -----------------------------------------


def test_forged_ownership_fields_422(auth_client):
    project, _, _ = _accepted_project(auth_client)
    for field, value in [
        ("project_id", str(uuid.uuid4())),
        ("team_id", str(uuid.uuid4())),
        ("user_id", str(uuid.uuid4())),
        ("created_by", str(uuid.uuid4())),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ]:
        resp = _post_invalid(
            auth_client, project["id"], _metric_payload(**{field: value})
        )
        assert resp.status_code == 422, (field, resp.json())


def test_forged_fields_rejected_on_patch(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"])
    payload = _metric_payload(value="999")
    payload.update({"user_id": str(uuid.uuid4()), "project_id": str(uuid.uuid4())})
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}", json=payload
    )
    assert resp.status_code == 422
    # The metric was not modified.
    assert auth_client.get(
        f"/api/projects/{project['id']}/impact"
    ).json()[0]["value"] == "120"


# --- Detail embedding + ordering ---------------------------------------------


def test_project_detail_contains_impact(auth_client):
    project, _, _ = _accepted_project(auth_client)
    _create_metric(auth_client, project["id"], name="First", value="1")
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "prototype"
    assert [m["name"] for m in detail["impact"]] == ["First"]


def test_metrics_ordered_by_created_at_asc(auth_client):
    project, _, _ = _accepted_project(auth_client)
    for name, value in [
        ("Households reached", "120"),
        ("Villages covered", "4"),
        ("Pilot participants", "85"),
    ]:
        _create_metric(auth_client, project["id"], name=name, value=value)
    resp = auth_client.get(f"/api/projects/{project['id']}/impact")
    assert resp.status_code == 200
    assert [m["name"] for m in resp.json()] == [
        "Households reached",
        "Villages covered",
        "Pilot participants",
    ]
    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert [m["name"] for m in detail["impact"]] == [
        "Households reached",
        "Villages covered",
        "Pilot participants",
    ]


# --- Lifecycle independence --------------------------------------------------


def test_impact_usable_at_prototype(auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert project["status"] == "prototype"
    metric = _create_metric(auth_client, project["id"])
    assert auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json=_metric_payload(value="130"),
    ).status_code == 200


def test_impact_usable_at_pilot(auth_client):
    project, _, _ = _accepted_project(auth_client)
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 200
    metric = _create_metric(auth_client, project["id"])
    assert auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json=_metric_payload(value="42"),
    ).status_code == 200
    assert auth_client.delete(
        f"/api/projects/{project['id']}/impact/{metric['id']}"
    ).status_code == 204


def test_impact_visible_and_editable_at_implemented(auth_client):
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"])
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 200
    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "implemented"}
    ).status_code == 200

    detail = auth_client.get(f"/api/projects/{project['id']}").json()
    assert detail["status"] == "implemented"
    assert [m["name"] for m in detail["impact"]] == ["Households reached"]

    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json=_metric_payload(value="150"),
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "150"


# --- Regression: CP5 offers + CP6 lifecycle ----------------------------------


def test_offers_respected_while_impact_editable(auth_client):
    """Impact and offers are independent: offers stay open through pilot and
    reject once implemented, while impact metrics remain editable throughout."""
    project, _, _ = _accepted_project(auth_client)
    metric = _create_metric(auth_client, project["id"])
    auth_client.post("/api/organizations", json={"name": "Impact FundCorp"})

    assert auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "funding", "message": "Pilot funding."},
    ).status_code == 201

    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "pilot"}
    ).status_code == 200
    assert auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "mentorship", "message": "Pilot guidance."},
    ).status_code == 201

    assert auth_client.patch(
        f"/api/projects/{project['id']}/lifecycle", json={"status": "implemented"}
    ).status_code == 200
    assert auth_client.post(
        f"/api/projects/{project['id']}/offers",
        json={"support_type": "equipment", "message": "Too late."},
    ).status_code == 409

    # Impact editing is unaffected by the terminal lifecycle state.
    resp = auth_client.patch(
        f"/api/projects/{project['id']}/impact/{metric['id']}",
        json=_metric_payload(value="200"),
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "200"