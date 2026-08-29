"""Phase 5 Checkpoint 4 — Proposal Review (institution owner/representative).

Covers: unauthenticated 401s, the authorization matrix (owner and
representative of the proposal's team institution may review; students,
ordinary team members, platform reviewers and other-institution owners are
forbidden), the review state machine (submitted -> under_review ->
accepted|rejected with rejected/accepted terminal, 409 on every invalid
transition), server control of status/reviewed_at/reviewed_by (+ 422 on
mass-assignment), review_note capture on the final decision, 404 handling,
the withdraw-hardening guard (no withdrawing a proposal the institution is
reviewing or has decided on), and CP3 regression (rejected proposals cannot
be resubmitted or edited).

Platform reviewers grant NO proposal-review rights (they only review
institutions). All authorization is derived from the database at request
time — never from client input.
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
    """Register an institution via the API (returns JSON)."""
    payload = {
        "name": "CP4 Test Institution",
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
        "title": "CP4 Test Challenge",
        "description": "Test challenge description for CP4 review tests.",
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
        "name": "CP4 Test Team",
        "description": "Test team description.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_proposal(c, team_id, challenge_id, **overrides):
    """Create a draft proposal via the API (returns JSON)."""
    payload = {
        "team_id": team_id,
        "challenge_id": challenge_id,
        "title": "CP4 Test Proposal",
        "summary": "Test proposal summary.",
        **overrides,
    }
    response = c.post("/api/proposals", json=payload)
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


def _add_team_member(
    db_session, team_id, user_id, role="member", status="active"
):
    """Insert a team membership row directly into the DB."""
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


def _team_context(auth_client):
    """Create institution + challenge + team under the auth_client owner/lead."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    return inst, ch, team


def _register_institution_member(
    db_session, user_client, email, institution_id, role="student", status="active"
):
    """Register a user and give them an institution membership row."""
    user_client(email)
    uid = _user_id(db_session, email)
    _create_membership(
        db_session, uid, uuid.UUID(institution_id), role, status=status
    )
    return uid


def _submitted_proposal(auth_client):
    """Institution (auth_client = owner + lead) with a submitted proposal."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    assert response.status_code == 200, response.json()
    return inst, ch, team, proposal


def _start_review(auth_client, proposal):
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 200, response.json()
    return response.json()


# --- Authentication -----------------------------------------------------------


def test_review_requires_auth(client, auth_client):
    """Unauthenticated review actions return 401."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    for action in ("start_review", "accept", "reject"):
        response = client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": action}
        )
        assert response.status_code == 401


# --- Authorization matrix -----------------------------------------------------


def test_owner_can_start_review(auth_client, user_client, db_session):
    """An ACTIVE institution owner (not a team member) starts the review."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    response = user_client("reviewer-owner@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "under_review"
    assert body["submitted_at"] is not None
    assert body["reviewed_at"] is None
    assert body["reviewed_by"] is None
    assert body["review_note"] is None


def test_representative_can_start_review(auth_client, user_client, db_session):
    """An ACTIVE institution representative (not a team member) can review."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session,
        user_client,
        "reviewer-rep@aikyra.dev",
        inst["id"],
        role="representative",
    )
    response = user_client("reviewer-rep@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_owner_who_is_also_team_lead_can_review(auth_client):
    """The institution owner (who created the team) reviews her own proposal."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_student_at_institution_cannot_review(auth_client, user_client, db_session):
    """A student at the institution cannot review proposals (403)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "student@aikyra.dev", inst["id"], role="student"
    )
    response = user_client("student@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 403


def test_team_member_without_review_role_cannot_review(
    auth_client, user_client, db_session
):
    """An ACTIVE team member who is not an owner/rep cannot review (403)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    response = user_client("member@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 403


def test_platform_reviewer_cannot_review_proposals(auth_client, reviewer_client):
    """Platform reviewer privilege grants no proposal-review rights (403)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = reviewer_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 403


def test_other_institution_owner_cannot_review(auth_client, user_client):
    """An owner of a DIFFERENT institution cannot review (403)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    other = user_client("other-owner@aikyra.dev")
    _create_institution(other, name="Other CP4 Institution")
    response = other.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 403


def test_suspended_owner_cannot_review(auth_client, user_client, db_session):
    """A suspended owner membership grants no review rights (403)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session,
        user_client,
        "suspended-owner@aikyra.dev",
        inst["id"],
        role="owner",
        status="suspended",
    )
    response = user_client("suspended-owner@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 403


# --- State machine: final decisions ------------------------------------------


def test_accept_proposal_success(auth_client, user_client, db_session):
    """accept sets status/reviewed_at/reviewed_by server-side from the reviewer."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    owner = user_client("reviewer-owner@aikyra.dev")
    _start_review(owner, proposal)
    response = owner.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["reviewed_at"] is not None
    assert body["reviewed_by"] == str(_user_id(db_session, "reviewer-owner@aikyra.dev"))

    # Accept materializes the approved-solution project (Phase 6 hook).
    projects = owner.get("/api/projects")
    assert projects.status_code == 200
    assert projects.json()["total"] == 1


def test_accept_proposal_with_note(auth_client, user_client, db_session):
    """A review note supplied at accept is persisted."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    owner = user_client("reviewer-owner@aikyra.dev")
    _start_review(owner, proposal)
    response = owner.post(
        f"/api/proposals/{proposal['id']}/review",
        json={"action": "accept", "review_note": "Approved by the institution."},
    )
    assert response.status_code == 200
    assert response.json()["review_note"] == "Approved by the institution."


def test_reject_proposal_with_note_success(auth_client, user_client, db_session):
    """reject moves under_review -> rejected and persists the review note."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    owner = user_client("reviewer-owner@aikyra.dev")
    _start_review(owner, proposal)
    response = owner.post(
        f"/api/proposals/{proposal['id']}/review",
        json={
            "action": "reject",
            "review_note": "Missing impact metrics and budget breakdown.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["reviewed_at"] is not None
    assert body["reviewed_by"] == str(_user_id(db_session, "reviewer-owner@aikyra.dev"))
    assert body["review_note"] == "Missing impact metrics and budget breakdown."


def test_reject_with_blank_note_stored_as_none(auth_client, user_client, db_session):
    """A whitespace-only review note is stored as null."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    owner = user_client("reviewer-owner@aikyra.dev")
    _start_review(owner, proposal)
    response = owner.post(
        f"/api/proposals/{proposal['id']}/review",
        json={"action": "reject", "review_note": "   "},
    )
    assert response.status_code == 200
    assert response.json()["review_note"] is None


def test_start_review_does_not_persist_note(auth_client, user_client, db_session):
    """review_note is only captured at the final decision, never at start."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _register_institution_member(
        db_session, user_client, "reviewer-owner@aikyra.dev", inst["id"], role="owner"
    )
    response = user_client("reviewer-owner@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/review",
        json={"action": "start_review", "review_note": "Not a decision."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"
    assert response.json()["review_note"] is None


# --- State machine: invalid transitions (409) ---------------------------------


def test_start_review_draft_conflict(auth_client):
    """A draft proposal cannot be moved into review (409)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 409


def test_start_review_already_under_review_conflict(auth_client):
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 409


def test_start_review_accepted_conflict(auth_client):
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
        ).status_code
        == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 409


def test_start_review_rejected_conflict(auth_client):
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
        ).status_code
        == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 409


def test_start_review_withdrawn_conflict(auth_client):
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert (
        auth_client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "start_review"}
    )
    assert response.status_code == 409


def test_accept_submitted_proposal_conflict(auth_client):
    """Accepting before start_review is a 409 (must be under review first)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert response.status_code == 409


def test_accept_draft_proposal_conflict(auth_client):
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert response.status_code == 409


def test_accept_already_accepted_conflict(auth_client):
    """accept is a one-way terminal transition (409 on a second accept)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
        ).status_code
        == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
    )
    assert response.status_code == 409


def test_reject_submitted_proposal_conflict(auth_client):
    """Rejecting before start_review is a 409."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
    )
    assert response.status_code == 409


def test_reject_already_rejected_conflict(auth_client):
    """reject is a one-way terminal transition (409 on a second reject)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
        ).status_code
        == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
    )
    assert response.status_code == 409


def test_reject_already_accepted_conflict(auth_client):
    """A proposal cannot be rejected after it has been accepted (409)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
        ).status_code
        == 200
    )
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
    )
    assert response.status_code == 409


# --- Withdraw-hardening guard (protects the review lifecycle) -----------------


def test_withdraw_under_review_conflict(auth_client):
    """A proposal under institution review cannot be withdrawn (409)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    response = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert response.status_code == 409


def test_withdraw_accepted_conflict(auth_client):
    """An accepted proposal cannot be withdrawn (409)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
        ).status_code
        == 200
    )
    response = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert response.status_code == 409


# --- Regression: rejected/accepted are terminal for the team ------------------


def test_rejected_proposal_cannot_resubmit_or_edit(auth_client):
    """A rejected proposal cannot be submitted or edited (409)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "reject"}
        ).status_code
        == 200
    )
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 409
    assert (
        auth_client.patch(
            f"/api/proposals/{proposal['id']}", json={"title": "Changed"}
        ).status_code
        == 409
    )


def test_accepted_proposal_edit_conflict(auth_client):
    """An accepted proposal is no longer editable (409)."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    _start_review(auth_client, proposal)
    assert (
        auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={"action": "accept"}
        ).status_code
        == 200
    )
    response = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "Changed"}
    )
    assert response.status_code == 409


# --- Not found ---------------------------------------------------------------


def test_review_nonexistent_proposal_404(auth_client):
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = auth_client.post(
        f"/api/proposals/{uuid.uuid4()}/review", json={"action": "start_review"}
    )
    assert response.status_code == 404


# --- Server-control / mass-assignment protection (422) -----------------------


def test_review_rejects_mass_assignment(auth_client, user_client, db_session):
    """status/reviewed_at/reviewed_by/team_id/challenge_id are never accepted."""
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    base = {"action": "accept"}
    for extra in (
        {"status": "accepted"},
        {"reviewed_at": "2026-08-29T00:00:00Z"},
        {"reviewed_by": str(uuid.uuid4())},
        {"team_id": team["id"]},
        {"challenge_id": ch["id"]},
    ):
        response = auth_client.post(
            f"/api/proposals/{proposal['id']}/review", json={**base, **extra}
        )
        assert response.status_code == 422, extra


def test_review_rejects_invalid_action(auth_client):
    inst, ch, team, proposal = _submitted_proposal(auth_client)
    response = auth_client.post(
        f"/api/proposals/{proposal['id']}/review", json={"action": "publish"}
    )
    assert response.status_code == 422