"""Phase 5 Checkpoint 3 — Solution Proposals (Core) tests.

Covers: draft creation (team-member only, team->challenge invariant, duplicate
(team, challenge) rejection, mass-assignment protection), list/detail scoping
(active team member or institution owner/representative only; students and
platform reviewers excluded), draft editing (draft-only state machine),
submission (lead-only, draft->submitted, submitted_at set server-side),
withdrawal (lead-only, terminal state), IDOR, cross-team/cross-institution
protection, the application-level race guard, and the database-level
UNIQUE(team_id, challenge_id) invariant.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.proposal import Proposal
from app.models.team import (
    TeamMembership,
    TeamMembershipStatus,
    TeamRole,
)


def _create_institution(c, **overrides):
    """Register an institution via the API (returns JSON)."""
    payload = {
        "name": "CP3 Test Institution",
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
        "title": "CP3 Test Challenge",
        "description": "Test challenge description for CP3 proposal tests.",
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
        "name": "CP3 Test Team",
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
        "title": "CP3 Test Proposal",
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


# --- Create: authorization ----------------------------------------------------


def test_create_proposal_requires_auth(client, auth_client):
    """Unauthenticated POST /api/proposals returns 401."""
    inst, ch, team = _team_context(auth_client)
    response = client.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"},
    )
    assert response.status_code == 401


def test_create_proposal_success(auth_client):
    """A team member creates a draft proposal (201, status=draft)."""
    inst, ch, team = _team_context(auth_client)
    response = auth_client.post(
        "/api/proposals",
        json={
            "team_id": team["id"],
            "challenge_id": ch["id"],
            "title": "Proposal Title",
            "summary": "Proposal summary text.",
            "approach": "Our approach.",
            "resources_needed": "Laptops and data.",
            "timeline": "3 months",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] == team["id"]
    assert body["challenge_id"] == ch["id"]
    assert body["title"] == "Proposal Title"
    assert body["summary"] == "Proposal summary text."
    assert body["approach"] == "Our approach."
    assert body["status"] == "draft"
    assert body["submitted_at"] is None
    assert body["reviewed_at"] is None
    assert body["reviewed_by"] is None
    assert body["review_note"] is None


def test_create_proposal_non_member_forbidden(auth_client, user_client, db_session):
    """A user with no team membership cannot create a proposal (403)."""
    inst, ch, team = _team_context(auth_client)
    outsider = user_client("outsider@aikyra.dev")
    response = outsider.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"},
    )
    assert response.status_code == 403


def test_create_proposal_non_active_membership_forbidden(
    auth_client, user_client, db_session
):
    """A non-active (invited) team membership cannot create a proposal (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_institution_member(
        db_session, user_client, "suspended@aikyra.dev", inst["id"]
    )
    _add_team_member(
        db_session, uuid.UUID(team["id"]), uid, status="invited"
    )
    suspended = user_client("suspended@aikyra.dev")
    response = suspended.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"},
    )
    assert response.status_code == 403


def test_create_proposal_nonexistent_team_404(auth_client):
    """Creating a proposal for a nonexistent team returns 404."""
    inst, ch, team = _team_context(auth_client)
    response = auth_client.post(
        "/api/proposals",
        json={
            "team_id": str(uuid.uuid4()),
            "challenge_id": ch["id"],
            "title": "x",
            "summary": "y",
        },
    )
    assert response.status_code == 404


def test_create_proposal_nonexistent_challenge_404(auth_client):
    """Creating a proposal for a nonexistent challenge returns 404."""
    inst, ch, team = _team_context(auth_client)
    response = auth_client.post(
        "/api/proposals",
        json={
            "team_id": team["id"],
            "challenge_id": str(uuid.uuid4()),
            "title": "x",
            "summary": "y",
        },
    )
    assert response.status_code == 404


def test_create_proposal_mismatched_challenge_conflict(auth_client):
    """challenge_id not matching the team's challenge is rejected with 409."""
    inst, ch, team = _team_context(auth_client)
    other = _create_challenge(auth_client, title="Different Challenge")
    response = auth_client.post(
        "/api/proposals",
        json={
            "team_id": team["id"],
            "challenge_id": other["id"],
            "title": "x",
            "summary": "y",
        },
    )
    assert response.status_code == 409


def test_create_proposal_duplicate_team_challenge_conflict(auth_client):
    """A second proposal for the same (team, challenge) returns 409."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"},
    )
    assert response.status_code == 409


def test_create_proposal_rejects_mass_assignment(auth_client):
    """Server-controlled fields are rejected with 422."""
    inst, ch, team = _team_context(auth_client)
    base = {"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"}

    with_status = {**base, "status": "submitted"}
    assert auth_client.post("/api/proposals", json=with_status).status_code == 422

    with_created_by = {**base, "created_by": str(uuid.uuid4())}
    assert auth_client.post("/api/proposals", json=with_created_by).status_code == 422

    with_submitted_at = {**base, "submitted_at": "2026-08-28T00:00:00Z"}
    assert auth_client.post("/api/proposals", json=with_submitted_at).status_code == 422

    with_reviewed_by = {**base, "reviewed_by": str(uuid.uuid4())}
    assert auth_client.post("/api/proposals", json=with_reviewed_by).status_code == 422

    assert auth_client.post("/api/proposals", json={**base, "review_note": "x"}).status_code == 422


def test_create_proposal_rejects_blank_title(auth_client):
    """Whitespace-only title is rejected with 422."""
    inst, ch, team = _team_context(auth_client)
    response = auth_client.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "   ", "summary": "y"},
    )
    assert response.status_code == 422


# --- List: visibility ----------------------------------------------------------


def test_list_proposals_requires_auth(client, auth_client):
    """Unauthenticated GET /api/proposals returns 401."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    assert client.get("/api/proposals").status_code == 401


def test_list_proposals_team_member_sees_own_team(
    auth_client, user_client, db_session
):
    """An active team member sees the team's proposals in the list."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    member = user_client("member@aikyra.dev")
    response = member.get("/api/proposals")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "CP3 Test Proposal"
    assert body["items"][0]["status"] == "draft"


def test_list_proposals_institution_owner_can_view(
    auth_client, user_client, db_session
):
    """An ACTIVE institution owner (not a team member) can view proposals."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    _register_institution_member(
        db_session, user_client, "owner@aikyra.dev", inst["id"], role="owner"
    )
    owner = user_client("owner@aikyra.dev")
    response = owner.get(f"/api/proposals?team_id={team['id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_proposals_institution_representative_can_view(
    auth_client, user_client, db_session
):
    """An ACTIVE institution representative can view proposals."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    _register_institution_member(
        db_session, user_client, "rep@aikyra.dev", inst["id"], role="representative"
    )
    rep = user_client("rep@aikyra.dev")
    response = rep.get(f"/api/proposals?team_id={team['id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_proposals_student_non_member_cannot_view(
    auth_client, user_client, db_session
):
    """A student at the institution (not a team member) sees no proposals."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    _register_institution_member(
        db_session, user_client, "student@aikyra.dev", inst["id"], role="student"
    )
    student = user_client("student@aikyra.dev")
    response = student.get(f"/api/proposals?team_id={team['id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_list_proposals_platform_reviewer_no_access(auth_client, reviewer_client):
    """The global platform reviewer privilege grants no proposal access."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    response = reviewer_client.get("/api/proposals")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_proposals_cross_team_filter_narrows_only(
    auth_client, user_client, db_session
):
    """A member of team B cannot see team A's proposals via filters."""
    inst, ch, team_a = _team_context(auth_client)
    team_b = _create_team(auth_client, inst["id"], ch["id"], name="Team B")
    proposal_a = _create_proposal(auth_client, team_a["id"], ch["id"])
    _create_proposal(auth_client, team_b["id"], ch["id"], title="Team B Proposal")

    uid = _register_institution_member(
        db_session, user_client, "b-member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team_b["id"]), uid)
    member_b = user_client("b-member@aikyra.dev")

    their_team = member_b.get(f"/api/proposals?team_id={team_b['id']}")
    assert their_team.status_code == 200
    assert their_team.json()["total"] == 1
    assert their_team.json()["items"][0]["title"] == "Team B Proposal"

    others_team = member_b.get(f"/api/proposals?team_id={team_a['id']}")
    assert others_team.status_code == 200
    assert others_team.json()["total"] == 0
    assert others_team.json()["items"] == []


def test_list_proposals_status_filter(auth_client):
    """The status filter narrows within the caller's visible scope."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    draft = auth_client.get(f"/api/proposals?team_id={team['id']}&status=draft")
    assert draft.status_code == 200
    assert draft.json()["total"] == 1
    submitted = auth_client.get(f"/api/proposals?team_id={team['id']}&status=submitted")
    assert submitted.status_code == 200
    assert submitted.json()["total"] == 0


# --- Detail: visibility --------------------------------------------------------


def test_get_proposal_requires_auth(client, auth_client):
    """Unauthenticated GET /api/proposals/{id} returns 401."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert client.get(f"/api/proposals/{proposal['id']}").status_code == 401


def test_get_proposal_team_member(auth_client, user_client, db_session):
    """An active team member can fetch proposal details."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    response = user_client("member@aikyra.dev").get(f"/api/proposals/{proposal['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "CP3 Test Proposal"


def test_get_proposal_owner_viewable_student_forbidden(
    auth_client, user_client, db_session
):
    """Owner can view a proposal; a student at the same institution cannot."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    _register_institution_member(
        db_session, user_client, "owner@aikyra.dev", inst["id"], role="owner"
    )
    _register_institution_member(
        db_session, user_client, "student@aikyra.dev", inst["id"], role="student"
    )
    owner_response = user_client("owner@aikyra.dev").get(
        f"/api/proposals/{proposal['id']}"
    )
    assert owner_response.status_code == 200
    student_response = user_client("student@aikyra.dev").get(
        f"/api/proposals/{proposal['id']}"
    )
    assert student_response.status_code == 403


def test_get_proposal_other_team_member_forbidden(
    auth_client, user_client, db_session
):
    """A member of a different team cannot fetch another team's proposal (403)."""
    inst, ch, team_a = _team_context(auth_client)
    team_b = _create_team(auth_client, inst["id"], ch["id"], name="Team B")
    proposal = _create_proposal(auth_client, team_a["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "b-member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team_b["id"]), uid)
    response = user_client("b-member@aikyra.dev").get(
        f"/api/proposals/{proposal['id']}"
    )
    assert response.status_code == 403


def test_get_proposal_other_institution_owner_forbidden(
    auth_client, user_client, db_session
):
    """An owner of a DIFFERENT institution cannot view this proposal (403)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    other = user_client("other-owner@aikyra.dev")
    _create_institution(other, name="Other Inst")
    response = other.get(f"/api/proposals/{proposal['id']}")
    assert response.status_code == 403


def test_get_proposal_not_found(auth_client):
    """Fetching a nonexistent proposal returns 404."""
    inst, ch, team = _team_context(auth_client)
    _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.get(f"/api/proposals/{uuid.uuid4()}")
    assert response.status_code == 404


# --- Edit: draft only -----------------------------------------------------------


def test_edit_draft_by_member_success(auth_client, user_client, db_session):
    """An active team member can edit a draft proposal."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    response = user_client("member@aikyra.dev").patch(
        f"/api/proposals/{proposal['id']}", json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    assert response.json()["status"] == "draft"


def test_edit_proposal_requires_auth(client, auth_client):
    """Unauthenticated PATCH /api/proposals/{id} returns 401."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert (
        client.patch(f"/api/proposals/{proposal['id']}", json={"title": "x"}).status_code
        == 401
    )


def test_edit_proposal_non_member_forbidden(auth_client, user_client, db_session):
    """A non-member cannot edit a proposal (403)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    outsider = user_client("outsider@aikyra.dev")
    response = outsider.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "x"}
    )
    assert response.status_code == 403


def test_edit_submitted_proposal_conflict(auth_client):
    """Editing a submitted proposal returns 409."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    response = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "x"}
    )
    assert response.status_code == 409


def test_edit_withdrawn_proposal_conflict(auth_client):
    """Editing a withdrawn proposal returns 409."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 200
    response = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "x"}
    )
    assert response.status_code == 409


def test_edit_proposal_rejects_server_fields(auth_client):
    """team_id/challenge_id/status cannot be changed via PATCH (422)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    with_team = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"team_id": str(uuid.uuid4())}
    )
    assert with_team.status_code == 422
    with_status = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"status": "submitted"}
    )
    assert with_status.status_code == 422


def test_edit_proposal_rejects_blank_title(auth_client):
    """Editing to a blank title returns 422."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "   "}
    )
    assert response.status_code == 422


def test_edit_proposal_rejects_null_title_and_summary(auth_client):
    """Editing with explicit null for required title/summary returns 422."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert (
        auth_client.patch(
            f"/api/proposals/{proposal['id']}", json={"title": None}
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/proposals/{proposal['id']}", json={"summary": None}
        ).status_code
        == 422
    )


def test_edit_proposal_can_clear_optional_field(auth_client):
    """Sending null clears an optional text field."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"], approach="Approach")
    response = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"approach": None}
    )
    assert response.status_code == 200
    assert response.json()["approach"] is None


# --- Submit: draft -> submitted, lead only ---------------------------------------


def test_submit_proposal_by_lead_success(auth_client):
    """The active team lead submits a draft; submitted_at is set server-side."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None
    assert body["reviewed_at"] is None
    assert body["reviewed_by"] is None
    assert body["review_note"] is None


def test_submit_proposal_requires_auth(client, auth_client):
    """Unauthenticated submit returns 401."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 401


def test_submit_proposal_non_lead_member_forbidden(
    auth_client, user_client, db_session
):
    """A non-lead team member cannot submit (403)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    response = user_client("member@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/submit"
    )
    assert response.status_code == 403


def test_submit_proposal_institution_owner_not_member_forbidden(
    auth_client, user_client, db_session
):
    """An institution owner who is not a team member cannot submit (403)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    _register_institution_member(
        db_session, user_client, "owner@aikyra.dev", inst["id"], role="owner"
    )
    response = user_client("owner@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/submit"
    )
    assert response.status_code == 403


def test_submit_already_submitted_proposal_conflict(auth_client):
    """Submitting an already-submitted proposal returns 409."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    response = auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    assert response.status_code == 409


def test_submit_withdrawn_proposal_conflict(auth_client):
    """Submitting a withdrawn proposal returns 409."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 200
    response = auth_client.post(f"/api/proposals/{proposal['id']}/submit")
    assert response.status_code == 409


# --- Withdraw: draft|submitted -> withdrawn, lead only ---------------------------


def test_withdraw_draft_proposal_by_lead_success(auth_client):
    """The active team lead withdraws a draft proposal."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    response = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_withdraw_submitted_proposal_by_lead_success(auth_client):
    """The active team lead withdraws a submitted proposal."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/submit").status_code == 200
    response = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_withdraw_proposal_non_lead_member_forbidden(
    auth_client, user_client, db_session
):
    """A non-lead team member cannot withdraw (403)."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    uid = _register_institution_member(
        db_session, user_client, "member@aikyra.dev", inst["id"]
    )
    _add_team_member(db_session, uuid.UUID(team["id"]), uid)
    response = user_client("member@aikyra.dev").post(
        f"/api/proposals/{proposal['id']}/withdraw"
    )
    assert response.status_code == 403


def test_withdraw_already_withdrawn_proposal_conflict(auth_client):
    """Withdrawing a withdrawn proposal returns 409."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 200
    response = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert response.status_code == 409


def test_withdraw_proposal_requires_auth(client, auth_client):
    """Unauthenticated withdraw returns 401."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 401


# --- Integrity: DB-level invariants --------------------------------------------


def test_db_unique_constraint_blocks_duplicate(auth_client, db_session):
    """UNIQUE(team_id, challenge_id) blocks a second proposal row directly."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    duplicate = Proposal(
        id=uuid.uuid4(),
        team_id=uuid.UUID(proposal["team_id"]),
        challenge_id=uuid.UUID(proposal["challenge_id"]),
        title="Duplicate",
        summary="Duplicate summary.",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_proposal_slot_consumed_by_withdrawal(auth_client):
    """Withdrawal is terminal — the (team, challenge) slot stays consumed."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])
    assert auth_client.post(f"/api/proposals/{proposal['id']}/withdraw").status_code == 200
    response = auth_client.post(
        "/api/proposals",
        json={"team_id": team["id"], "challenge_id": ch["id"], "title": "x", "summary": "y"},
    )
    assert response.status_code == 409


def test_cp4_review_fields_remain_null_and_reachable_states(auth_client):
    """Only draft/submitted/withdrawn are reachable; CP4 fields stay null."""
    inst, ch, team = _team_context(auth_client)
    proposal = _create_proposal(auth_client, team["id"], ch["id"])

    editable = auth_client.patch(
        f"/api/proposals/{proposal['id']}", json={"title": "Still Draft"}
    )
    assert editable.status_code == 200
    assert editable.json()["status"] == "draft"

    withdrawn = auth_client.post(f"/api/proposals/{proposal['id']}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert withdrawn.json()["submitted_at"] is None

    reselect = auth_client.get(f"/api/proposals?status=withdrawn")
    assert reselect.json()["total"] == 1
    assert reselect.json()["items"][0]["id"] == proposal["id"]