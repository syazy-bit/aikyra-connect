"""Phase 5 Checkpoint 2 — Team Invitations & Membership Flow tests.

Covers: invitation creation (lead-only, faculty/student invitee eligibility,
cross-institution rejection, duplicates), accept/decline (owner-of-invitation
only, accept-time re-validation), leaving teams (non-lead only; row deleted),
leadership transfer (atomic, exactly one active lead), pending-invitations
discovery, IDOR, mass-assignment protection, and the database-level
single-active-lead invariant.
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
from app.models.team import (
    TeamMembership,
    TeamMembershipStatus,
    TeamRole,
)


def _create_institution(c, **overrides):
    """Register an institution via the API (returns JSON)."""
    payload = {
        "name": "CP2 Test Institution",
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
        "title": "CP2 Test Challenge",
        "description": "Test challenge description for CP2 invitation tests.",
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
        "name": "CP2 Test Team",
        "description": "Test team description.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
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


def _user_id(db_session, email):
    from app.models.user import User

    return db_session.query(User).filter(User.email == email).first().id


def _team_context(auth_client):
    """Create institution + challenge + team under the auth_client admin/lead."""
    inst = _create_institution(auth_client)
    ch = _create_challenge(auth_client)
    team = _create_team(auth_client, inst["id"], ch["id"])
    return inst, ch, team


def _register_with_membership(
    db_session, user_client, email, institution_id, role="student", status="active"
):
    """Register a user and give them an institution membership row."""
    user_client(email)
    uid = _user_id(db_session, email)
    _create_membership(
        db_session, uid, uuid.UUID(institution_id), role, status=status
    )
    return uid


def _invite(lead_client, team_id, user_id):
    response = lead_client.post(
        f"/api/teams/{team_id}/invitations", json={"user_id": str(user_id)}
    )
    return response


# --- Invitation creation: authorization ---------------------------------------


def test_invite_requires_auth(client, auth_client, user_client, db_session):
    """Unauthenticated POST /api/teams/{id}/invitations returns 401."""
    inst, ch, team = _team_context(auth_client)
    who = user_client("invitee@aikyra.dev")
    _create_membership(db_session, _user_id(db_session, "invitee@aikyra.dev"),
                       uuid.UUID(inst["id"]), "student")
    response = client.post(
        f"/api/teams/{team['id']}/invitations",
        json={"user_id": str(_user_id(db_session, "invitee@aikyra.dev"))},
    )
    assert response.status_code == 401


def test_lead_invites_faculty_success(auth_client, user_client, db_session):
    """The active lead can invite a faculty member; the row is status invited."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "facultyinv@aikyra.dev", inst["id"], role="faculty"
    )
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "invited"
    assert body["role"] == "member"
    assert body["invited_by"] == str(_user_id(db_session, "auth@aikyra.dev"))
    assert body["joined_at"] is None


def test_lead_invites_student_success(auth_client, user_client, db_session):
    """The active lead can invite a student member."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "studentinv@aikyra.dev", inst["id"], role="student"
    )
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 201, response.json()


def test_non_lead_member_cannot_invite(auth_client, user_client, db_session):
    """An active non-lead member cannot create an invitation (403)."""
    inst, ch, team = _team_context(auth_client)
    member_uid = _register_with_membership(
        db_session, user_client, "member@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], member_uid)
    assert invite.status_code == 201
    member = user_client("member@aikyra.dev")
    member.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")
    target_uid = _register_with_membership(
        db_session, user_client, "target@aikyra.dev", inst["id"], role="faculty"
    )
    response = _invite(member, team["id"], target_uid)
    assert response.status_code == 403


def test_platform_reviewer_cannot_invite(auth_client, reviewer_client, user_client, db_session):
    """The global platform reviewer privilege grants no team invitation power."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "revtarget@aikyra.dev", inst["id"], role="student"
    )
    response = reviewer_client.post(
        f"/api/teams/{team['id']}/invitations", json={"user_id": str(uid)}
    )
    assert response.status_code == 403


def test_unrelated_user_cannot_invite(auth_client, user_client, db_session):
    """A user with no team membership cannot invite (403)."""
    inst, ch, team = _team_context(auth_client)
    outsider_client = user_client("outsider@aikyra.dev")
    uid = _register_with_membership(
        db_session, user_client, "victim@aikyra.dev", inst["id"], role="student"
    )
    response = outsider_client.post(
        f"/api/teams/{team['id']}/invitations", json={"user_id": str(uid)}
    )
    assert response.status_code == 403


def test_invite_nonexistent_team_404(auth_client, user_client, db_session):
    """Inviting on a nonexistent team returns 404."""
    inst = _create_institution(auth_client, name="Ghost Team Inst")
    uid = _register_with_membership(
        db_session, user_client, "ghost@aikyra.dev", inst["id"], role="student"
    )
    response = _invite(auth_client, uuid.uuid4(), uid)
    assert response.status_code == 404


def test_invite_nonexistent_user_404(auth_client):
    """Inviting a nonexistent user returns 404."""
    inst, ch, team = _team_context(auth_client)
    response = _invite(auth_client, team["id"], uuid.uuid4())
    assert response.status_code == 404


# --- Invitation creation: invitee eligibility ----------------------------------


def test_invitee_without_institution_membership_forbidden(
    auth_client, user_client, db_session
):
    """A user with no institution membership cannot be invited (403)."""
    inst, ch, team = _team_context(auth_client)
    nobody = user_client("nobody@aikyra.dev")
    uid = _user_id(db_session, "nobody@aikyra.dev")
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 403


def test_invitee_admin_role_forbidden(auth_client, user_client, db_session):
    """An institution_admin (institution role) at the team's institution is not
    a valid invitee target (403)."""
    inst, ch, team = _team_context(auth_client)
    admin = user_client("admin2@aikyra.dev")
    admin_uid = _user_id(db_session, "admin2@aikyra.dev")
    _create_membership(db_session, admin_uid, uuid.UUID(inst["id"]), "institution_admin")
    response = _invite(auth_client, team["id"], admin_uid)
    assert response.status_code == 403


def test_invitee_representative_role_forbidden(auth_client, user_client, db_session):
    """A representative is not a valid invitee target (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "rep2@aikyra.dev", inst["id"], role="representative"
    )
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 403


def test_invitee_suspended_institution_membership_forbidden(
    auth_client, user_client, db_session
):
    """A suspended institution membership is not an active faculty/student (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "suspended@aikyra.dev", inst["id"],
        role="student", status="suspended",
    )
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 403


def test_invitee_invited_status_institution_membership_forbidden(
    auth_client, user_client, db_session
):
    """An invited (non-active) institution membership is not eligible (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "instinvitee@aikyra.dev", inst["id"],
        role="student", status="invited",
    )
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 403


def test_cross_institution_invite_forbidden(auth_client, user_client, db_session):
    """A faculty/student of a DIFFERENT institution cannot be invited (403)."""
    inst, ch, team = _team_context(auth_client)
    outsider = user_client("cross@aikyra.dev")
    # Creating another institution makes the user its owner — they hold no
    # membership at the team's institution, so they must not be invitable.
    _create_institution(outsider, name="Other Inst")
    uid = _user_id(db_session, "cross@aikyra.dev")
    response = _invite(auth_client, team["id"], uid)
    assert response.status_code == 403


# --- Invitation creation: duplicates -----------------------------------------


def test_invite_current_member_conflict(auth_client, user_client, db_session):
    """Inviting an already-active team member returns 409."""
    inst, ch, team = _team_context(auth_client)
    lead_uid = _user_id(db_session, "auth@aikyra.dev")
    response = _invite(auth_client, team["id"], lead_uid)
    assert response.status_code == 409


def test_duplicate_pending_invite_conflict(auth_client, user_client, db_session):
    """Inviting a user who already has a pending invitation returns 409."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "dup@aikyra.dev", inst["id"], role="faculty"
    )
    first = _invite(auth_client, team["id"], uid)
    assert first.status_code == 201
    second = _invite(auth_client, team["id"], uid)
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_reinvite_after_decline_succeeds(auth_client, user_client, db_session):
    """After an invitee declines, a fresh invite is allowed (201)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "reinvite@aikyra.dev", inst["id"], role="faculty"
    )
    first = _invite(auth_client, team["id"], uid)
    assert first.status_code == 201
    invitee = user_client("reinvite@aikyra.dev")
    decline = invitee.post(
        f"/api/teams/{team['id']}/invitations/{first.json()['id']}/decline"
    )
    assert decline.status_code == 200
    second = _invite(auth_client, team["id"], uid)
    assert second.status_code == 201


# --- Accept -------------------------------------------------------------------


def test_invitee_accepts_success(auth_client, user_client, db_session):
    """Accepting turns invited -> active and sets joined_at server-side."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "accept@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    assert invite.status_code == 201
    invitee = user_client("accept@aikyra.dev")
    before = datetime.now(timezone.utc)
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["status"] == "active"
    assert body["role"] == "member"
    assert body["joined_at"] is not None
    assert body["invited_by"] == str(_user_id(db_session, "auth@aikyra.dev"))
    assert body["status"] == "active"


def test_accept_revalidates_institution_membership(
    auth_client, user_client, db_session
):
    """Accept-time re-validation: suspended institution membership -> 403 (D3)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "reval@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    assert invite.status_code == 201

    # Suspend the invitee's institution membership before they accept.
    from app.models.institution_membership import InstitutionMembership as InstMem

    inst_mem = (
        db_session.query(InstMem)
        .filter(
            InstMem.user_id == uid,
            InstMem.institution_id == uuid.UUID(inst["id"]),
        )
        .first()
    )
    inst_mem.status = InstitutionMembershipStatus.SUSPENDED
    db_session.commit()

    invitee = user_client("reval@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert response.status_code == 403


def test_accept_other_users_invitation_forbidden(auth_client, user_client, db_session):
    """IDOR: user B cannot accept user A's invitation even knowing the
    membership_id (403)."""
    inst, ch, team = _team_context(auth_client)
    uid_a = _register_with_membership(
        db_session, user_client, "ida@aikyra.dev", inst["id"], role="student"
    )
    uid_b = _register_with_membership(
        db_session, user_client, "idb@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid_a)
    assert invite.status_code == 201

    user_b = user_client("idb@aikyra.dev")
    response = user_b.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert response.status_code == 403


def test_accept_membership_from_other_team_404(auth_client, user_client, db_session):
    """An invitation from team A referenced via team B's path returns 404."""
    inst, ch, team_a = _team_context(auth_client)
    team_b = _create_team(auth_client, inst["id"], ch["id"], name="Team B")
    uid = _register_with_membership(
        db_session, user_client, "crossaccept@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team_a["id"], uid)
    assert invite.status_code == 201
    invitee = user_client("crossaccept@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team_b['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert response.status_code == 404


def test_accept_nonexistent_membership_404(auth_client, user_client, db_session):
    """Accepting a nonexistent membership returns 404."""
    inst, ch, team = _team_context(auth_client)
    _register_with_membership(
        db_session, user_client, "ghostaccept@aikyra.dev", inst["id"], role="student"
    )
    invitee = user_client("ghostaccept@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{uuid.uuid4()}/accept"
    )
    assert response.status_code == 404


def test_accept_malformed_membership_id_422(auth_client, user_client, db_session):
    """A malformed membership id is rejected by path validation (422)."""
    inst, ch, team = _team_context(auth_client)
    _register_with_membership(
        db_session, user_client, "badaccept@aikyra.dev", inst["id"], role="student"
    )
    invitee = user_client("badaccept@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/not-a-uuid/accept"
    )
    assert response.status_code == 422


def test_accept_already_active_conflict(auth_client, user_client, db_session):
    """Accepting an already-accepted invitation returns 409."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "twice@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    invitee = user_client("twice@aikyra.dev")
    first = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert first.status_code == 200
    second = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert second.status_code == 409


def test_accept_after_decline_missing_404(auth_client, user_client, db_session):
    """Accepting an invitation that was already declined (row gone) -> 404."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "lateaccept@aikyra.dev", inst["id"], role="faculty"
    )
    invite = _invite(auth_client, team["id"], uid)
    invitee = user_client("lateaccept@aikyra.dev")
    assert invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/decline"
    ).status_code == 200
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
    )
    assert response.status_code == 404


# --- Decline ------------------------------------------------------------------


def test_decline_removes_row(auth_client, user_client, db_session):
    """Declining removes the invitation row (D1)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "decline@aikyra.dev", inst["id"], role="faculty"
    )
    invite = _invite(auth_client, team["id"], uid)
    invite_id = uuid.UUID(invite.json()["id"])
    invitee = user_client("decline@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite_id}/decline"
    )
    assert response.status_code == 200
    row = (
        db_session.query(TeamMembership)
        .filter(TeamMembership.id == invite_id)
        .first()
    )
    assert row is None


def test_decline_other_users_invitation_forbidden(
    auth_client, user_client, db_session
):
    """IDOR: user B cannot decline user A's invitation even knowing the
    membership_id (403)."""
    inst, ch, team = _team_context(auth_client)
    uid_a = _register_with_membership(
        db_session, user_client, "decida@aikyra.dev", inst["id"], role="student"
    )
    uid_b = _register_with_membership(
        db_session, user_client, "decidb@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid_a)
    user_b = user_client("decidb@aikyra.dev")
    response = user_b.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/decline"
    )
    assert response.status_code == 403


def test_decline_after_accept_conflict(auth_client, user_client, db_session):
    """Declining an already-accepted invitation returns 409."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "declafter@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    invitee = user_client("declafter@aikyra.dev")
    invitee.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/decline"
    )
    assert response.status_code == 409


def test_decline_nonexistent_404(auth_client, user_client, db_session):
    """Declining a nonexistent membership returns 404."""
    inst, ch, team = _team_context(auth_client)
    _register_with_membership(
        db_session, user_client, "ghostdecline@aikyra.dev", inst["id"], role="student"
    )
    invitee = user_client("ghostdecline@aikyra.dev")
    response = invitee.post(
        f"/api/teams/{team['id']}/invitations/{uuid.uuid4()}/decline"
    )
    assert response.status_code == 404


# --- Leaving teams ------------------------------------------------------------


def test_active_member_leaves_row_deleted(auth_client, user_client, db_session):
    """An active non-lead member leaving deletes the membership row (D1)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "leaver@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    leaver = user_client("leaver@aikyra.dev")
    leaver.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")
    membership_id = uuid.UUID(invite.json()["id"])

    response = leaver.post(f"/api/teams/{team['id']}/leave")
    assert response.status_code == 200
    row = (
        db_session.query(TeamMembership)
        .filter(TeamMembership.id == membership_id)
        .first()
    )
    assert row is None


def test_lead_cannot_leave_conflict(auth_client):
    """The active lead cannot leave until leadership is transferred (409)."""
    inst, ch, team = _team_context(auth_client)
    response = auth_client.post(f"/api/teams/{team['id']}/leave")
    assert response.status_code == 409
    assert "transfer" in response.json()["detail"].lower()


def test_lead_leaves_after_transfer(auth_client, user_client, db_session):
    """After transferring leadership, the former lead can leave (200)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "newlead@aikyra.dev", inst["id"], role="faculty"
    )
    invite = _invite(auth_client, team["id"], uid)
    new_lead = user_client("newlead@aikyra.dev")
    new_lead.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")

    transfer = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(uid)},
    )
    assert transfer.status_code == 200

    leave = auth_client.post(f"/api/teams/{team['id']}/leave")
    assert leave.status_code == 200


def test_non_member_leave_forbidden(auth_client, user_client, db_session):
    """A user with no active team membership cannot leave (403)."""
    inst, ch, team = _team_context(auth_client)
    stranger = user_client("stranger@aikyra.dev")
    response = stranger.post(f"/api/teams/{team['id']}/leave")
    assert response.status_code == 403


def test_invited_user_cannot_leave(auth_client, user_client, db_session):
    """A pending invitee (status invited) cannot leave — must decline instead (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "invitedleave@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    invitee = user_client("invitedleave@aikyra.dev")
    response = invitee.post(f"/api/teams/{team['id']}/leave")
    assert response.status_code == 403
    row = (
        db_session.query(TeamMembership)
        .filter(TeamMembership.id == uuid.UUID(invite.json()["id"]))
        .first()
    )
    assert row is not None
    assert row.status == TeamMembershipStatus.INVITED


def test_leave_requires_auth(client, auth_client):
    """Unauthenticated leave returns 401."""
    inst, ch, team = _team_context(auth_client)
    response = client.post(f"/api/teams/{team['id']}/leave")
    assert response.status_code == 401


# --- Leadership transfer ------------------------------------------------------


def test_transfer_leadership_success(auth_client, user_client, db_session):
    """Transfer demotes the old lead and promotes the target; exactly one lead."""
    inst, ch, team = _team_context(auth_client)
    old_lead_uid = _user_id(db_session, "auth@aikyra.dev")
    uid = _register_with_membership(
        db_session, user_client, "becomelead@aikyra.dev", inst["id"], role="faculty"
    )
    invite = _invite(auth_client, team["id"], uid)
    new_lead = user_client("becomelead@aikyra.dev")
    new_lead.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")

    transfer = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(uid)},
    )
    assert transfer.status_code == 200
    assert transfer.json()["role"] == "lead"
    assert transfer.json()["status"] == "active"

    rows = db_session.query(TeamMembership).filter(
        TeamMembership.team_id == uuid.UUID(team["id"]),
        TeamMembership.status == TeamMembershipStatus.ACTIVE,
    ).all()
    leads = [m for m in rows if m.role == TeamRole.LEAD]
    assert len(leads) == 1
    assert leads[0].user_id == uid
    old = [m for m in rows if m.user_id == old_lead_uid][0]
    assert old.role == TeamRole.MEMBER


def test_transfer_by_non_lead_forbidden(auth_client, user_client, db_session):
    """A non-lead member cannot transfer leadership (403)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "notlead@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    member = user_client("notlead@aikyra.dev")
    member.post(f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept")
    response = member.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(_user_id(db_session, "auth@aikyra.dev"))},
    )
    assert response.status_code == 403


def test_transfer_to_non_member_conflict(auth_client, user_client, db_session):
    """Transferring leadership to a non-member returns 409."""
    inst, ch, team = _team_context(auth_client)
    ghost_uid = _register_with_membership(
        db_session, user_client, "ghostlead@aikyra.dev", inst["id"], role="student"
    )
    response = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(ghost_uid)},
    )
    assert response.status_code == 409


def test_transfer_to_self_conflict(auth_client, db_session):
    """Transferring leadership to the current lead returns 409."""
    inst, ch, team = _team_context(auth_client)
    self_uid = _user_id(db_session, "auth@aikyra.dev")
    response = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(self_uid)},
    )
    assert response.status_code == 409


def test_transfer_chain_keeps_single_lead(auth_client, user_client, db_session):
    """Sequential transfers always leave exactly one active lead."""
    inst, ch, team = _team_context(auth_client)
    lead_a_uid = _register_with_membership(
        db_session, user_client, "chaina@aikyra.dev", inst["id"], role="student"
    )
    lead_b_uid = _register_with_membership(
        db_session, user_client, "chainb@aikyra.dev", inst["id"], role="student"
    )
    for email in ("chaina@aikyra.dev", "chainb@aikyra.dev"):
        invite = _invite(auth_client, team["id"], _user_id(db_session, email))
        assert invite.status_code == 201
        member = user_client(email)
        assert member.post(
            f"/api/teams/{team['id']}/invitations/{invite.json()['id']}/accept"
        ).status_code == 200

    first = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(lead_a_uid)},
    )
    assert first.status_code == 200
    new_lead_a = user_client("chaina@aikyra.dev")
    second = new_lead_a.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(lead_b_uid)},
    )
    assert second.status_code == 200

    rows = db_session.query(TeamMembership).filter(
        TeamMembership.team_id == uuid.UUID(team["id"]),
        TeamMembership.status == TeamMembershipStatus.ACTIVE,
    ).all()
    leads = [m for m in rows if m.role == TeamRole.LEAD]
    assert len(leads) == 1
    assert leads[0].user_id == lead_b_uid


def test_second_active_lead_insert_integrity_error(
    auth_client, user_client, db_session
):
    """The database partial unique index rejects a second active lead (D5)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "dbguard@aikyra.dev", inst["id"], role="student"
    )
    duplicate_lead = TeamMembership(
        id=uuid.uuid4(),
        team_id=uuid.UUID(team["id"]),
        user_id=uid,
        role=TeamRole.LEAD,
        status=TeamMembershipStatus.ACTIVE,
    )
    db_session.add(duplicate_lead)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- Pending invitations discovery (D4) ---------------------------------------


def test_invitations_me_returns_only_own(auth_client, user_client, db_session):
    """GET /api/teams/invitations/me returns only the caller's invitations."""
    inst, ch, team = _team_context(auth_client)
    uid_a = _register_with_membership(
        db_session, user_client, "mea@aikyra.dev", inst["id"], role="student"
    )
    uid_b = _register_with_membership(
        db_session, user_client, "meb@aikyra.dev", inst["id"], role="student"
    )
    inv_a = _invite(auth_client, team["id"], uid_a)
    _invite(auth_client, team["id"], uid_b)
    assert inv_a.status_code == 201

    user_a = user_client("mea@aikyra.dev")
    response = user_a.get("/api/teams/invitations/me")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == inv_a.json()["id"]
    assert body["items"][0]["team_id"] == team["id"]


def test_invitations_me_without_team_membership(auth_client, user_client, db_session):
    """The invitee can list their invitation before joining any team (D4)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "prescan@aikyra.dev", inst["id"], role="student"
    )
    invite = _invite(auth_client, team["id"], uid)
    assert invite.status_code == 201
    invitee = user_client("prescan@aikyra.dev")
    response = invitee.get("/api/teams/invitations/me")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_invitations_me_empty(auth_client, user_client, db_session):
    """A user with no pending invitations gets an empty list."""
    user = user_client("empty@aikyra.dev")
    response = user.get("/api/teams/invitations/me")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_invitations_me_requires_auth(client):
    """Unauthenticated GET /api/teams/invitations/me returns 401."""
    response = client.get("/api/teams/invitations/me")
    assert response.status_code == 401


# --- Mass-assignment protection ------------------------------------------------


def test_invite_rejects_mass_assignment(auth_client, user_client, db_session):
    """Invite body cannot carry role/status/invited_by (extra='forbid' -> 422)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "mass@aikyra.dev", inst["id"], role="student"
    )
    response = auth_client.post(
        f"/api/teams/{team['id']}/invitations",
        json={
            "user_id": str(uid),
            "role": "lead",
            "status": "active",
            "invited_by": str(uuid.uuid4()),
            "joined_at": "2099-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 422


def test_transfer_rejects_mass_assignment(auth_client, user_client, db_session):
    """Leadership body cannot carry extra server-controlled fields (422)."""
    inst, ch, team = _team_context(auth_client)
    uid = _register_with_membership(
        db_session, user_client, "masstrans@aikyra.dev", inst["id"], role="student"
    )
    response = auth_client.post(
        f"/api/teams/{team['id']}/leadership",
        json={"new_lead_user_id": str(uid), "team_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422