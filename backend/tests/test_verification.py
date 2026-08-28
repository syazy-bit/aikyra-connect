"""Phase 4C Checkpoint 3 — Verification Workflow tests (Platform Reviewer).

Covers: verification state machine, platform reviewer authorization,
security controls, server-controlled fields, and invalid transition
rejection.

Architecture: platform reviewers are global Aikyra staff who can verify
ANY institution without needing an institution membership. Institution
owners/representatives manage their institution and submit for review.
"""

import uuid

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)
from app.models.user import User

MINIMAL_PAYLOAD = {
    "name": "Village Innovation Hub",
    "institution_type": "innovation_hub",
    "location": "Tumakuru, Karnataka",
}


def _create_institution(c, **overrides):
    """Register an institution via the API (returns JSON)."""
    body = {**MINIMAL_PAYLOAD, **overrides}
    response = c.post("/api/institutions", json=body)
    assert response.status_code == 201, response.json()
    return response.json()


def _create_membership(db_session, user_id, institution_id, role, status="active"):
    """Insert a membership row directly into the DB."""
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


def _get_user_id(db_session, email):
    """Fetch a user ID by email."""
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None, f"User {email} not found"
    return user.id


def _verify(c, institution_id, note=None):
    """Send a verification action."""
    body = {"action": "verify"}
    if note:
        body["note"] = note
    return c.patch(f"/api/institutions/{institution_id}/verification", json=body)


def _reject(c, institution_id, note=None):
    body = {"action": "reject"}
    if note:
        body["note"] = note
    return c.patch(f"/api/institutions/{institution_id}/verification", json=body)


def _submit(c, institution_id):
    return c.patch(
        f"/api/institutions/{institution_id}/verification",
        json={"action": "submit_for_review"},
    )


def _resubmit(c, institution_id):
    return c.patch(
        f"/api/institutions/{institution_id}/verification",
        json={"action": "resubmit"},
    )


def _suspend(c, institution_id, note=None):
    body = {"action": "suspend"}
    if note:
        body["note"] = note
    return c.patch(f"/api/institutions/{institution_id}/verification", json=body)


def _reinstate(c, institution_id, note=None):
    body = {"action": "reinstate"}
    if note:
        body["note"] = note
    return c.patch(f"/api/institutions/{institution_id}/verification", json=body)


# --- Core workflow tests --------------------------------------------------------


def test_submit_for_review(auth_client, db_session):
    """Owner submits an unverified institution -> pending_review."""
    inst = _create_institution(auth_client)
    resp = _submit(auth_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "pending_review"


def test_submit_for_review_requires_auth(client):
    """Unauthenticated submit returns 401."""
    resp = client.patch(
        f"/api/institutions/{uuid.uuid4()}/verification",
        json={"action": "submit_for_review"},
    )
    assert resp.status_code == 401


def test_platform_reviewer_cannot_submit(auth_client, reviewer_client, db_session):
    """A platform reviewer without owner/rep membership cannot submit
    for review (submit is owner/representative-only)."""
    inst = _create_institution(auth_client)
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_platform_reviewer_can_submit_with_rep_membership(
    auth_client, reviewer_client, db_session
):
    """With a representative membership, a user (even a platform reviewer)
    can submit for review. Submit is driven by institution membership."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(
        db_session, reviewer_id, uuid.UUID(inst["id"]), "representative"
    )
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "pending_review"


def test_verify_by_platform_reviewer(auth_client, reviewer_client, db_session):
    """Platform reviewer verifies a pending institution -> verified."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "verified"
    assert body["verified_by"] == str(reviewer_id)
    assert body["verified_at"] is not None


def test_platform_reviewer_verify_without_membership(
    auth_client, reviewer_client, db_session
):
    """A platform reviewer can verify an institution with NO membership."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")

    # Assert reviewer has no membership on this institution
    membership = db_session.query(InstitutionMembership).filter(
        InstitutionMembership.user_id == reviewer_id,
        InstitutionMembership.institution_id == uuid.UUID(inst["id"]),
    ).first()
    assert membership is None

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "verified"
    assert resp.json()["verified_by"] == str(reviewer_id)


def test_platform_reviewer_can_verify_multiple_institutions(
    auth_client, reviewer_client, db_session
):
    """A platform reviewer can verify ANY institution across the platform."""
    inst_a = _create_institution(
        auth_client, name="University A", website="https://a.example.com"
    )
    inst_b = _create_institution(
        auth_client, name="University B", website="https://b.example.com"
    )
    inst_c = _create_institution(
        auth_client, name="University C", website="https://c.example.com"
    )

    _submit(auth_client, inst_a["id"])
    _submit(auth_client, inst_b["id"])
    _submit(auth_client, inst_c["id"])

    for inst in (inst_a, inst_b, inst_c):
        resp = _verify(reviewer_client, inst["id"])
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "verified"


def test_owner_cannot_verify(auth_client, db_session):
    """An institution owner (not a platform reviewer) cannot verify."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(auth_client, inst["id"])
    assert resp.status_code == 403


def test_reject_by_platform_reviewer(auth_client, reviewer_client, db_session):
    """Platform reviewer rejects a pending institution -> rejected."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _reject(reviewer_client, inst["id"], note="Needs more documentation.")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "rejected"
    assert body["verification_note"] == "Needs more documentation."


def test_resubmit_after_rejection(auth_client, reviewer_client, db_session):
    """Owner resubmits a rejected institution -> pending_review."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _reject(reviewer_client, inst["id"])

    resp = _resubmit(auth_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "pending_review"
    assert body["verified_by"] is None
    assert body["verified_at"] is None
    assert body["verification_note"] is None


def test_suspend_by_platform_reviewer(auth_client, reviewer_client, db_session):
    """Platform reviewer suspends a verified institution -> suspended."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])

    resp = _suspend(reviewer_client, inst["id"], note="Policy violation.")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "suspended"
    assert body["verification_note"] == "Policy violation."


def test_reinstate_by_platform_reviewer(auth_client, reviewer_client, db_session):
    """Platform reviewer reinstates a suspended institution -> verified."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    _suspend(reviewer_client, inst["id"])

    resp = _reinstate(reviewer_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "verified"


# --- Invalid transition tests ---------------------------------------------------


def test_invalid_transition_verified_to_unverified(
    auth_client, reviewer_client, db_session
):
    """verified -> submit_for_review is invalid (409)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])

    resp = _submit(auth_client, inst["id"])
    assert resp.status_code == 409
    assert "Cannot perform" in resp.json()["detail"]


def test_invalid_transition_rejected_to_verified(
    auth_client, reviewer_client, db_session
):
    """rejected -> verified directly is invalid (409)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _reject(reviewer_client, inst["id"])

    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 409


def test_submit_for_review_from_pending_only(auth_client, db_session):
    """submit_for_review on an already-pending institution -> 409."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _submit(auth_client, inst["id"])
    assert resp.status_code == 409


def test_invalid_transition_suspended_to_verify_directly(
    auth_client, reviewer_client, db_session
):
    """suspended -> verify directly is invalid (409)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    _suspend(reviewer_client, inst["id"])

    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 409


# --- Audit field tests ----------------------------------------------------------


def test_verify_sets_verified_by_and_verified_at(
    auth_client, reviewer_client, db_session
):
    """verify populates verified_by and verified_at."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    body = resp.json()
    assert body["verified_by"] == str(reviewer_id)
    assert body["verified_at"] is not None


def test_verify_sets_note(auth_client, reviewer_client, db_session):
    """verify persists the reviewer's note."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"], note="Looks good.")
    assert resp.json()["verification_note"] == "Looks good."


# --- Security regression tests --------------------------------------------------


def test_unauthenticated_verification_request(client):
    """No token -> 401."""
    resp = client.patch(
        f"/api/institutions/{uuid.uuid4()}/verification",
        json={"action": "submit_for_review"},
    )
    assert resp.status_code == 401


def test_invalid_token_verification_request(client):
    """Invalid token -> 401."""
    resp = client.patch(
        f"/api/institutions/{uuid.uuid4()}/verification",
        json={"action": "submit_for_review"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401


def test_unrelated_user_cannot_submit(auth_client, reviewer_client, db_session):
    """An authenticated user without owner/rep membership cannot submit."""
    inst = _create_institution(auth_client)
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_owner_cannot_reject(auth_client, db_session):
    """Owner cannot reject (platform reviewer only)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _reject(auth_client, inst["id"])
    assert resp.status_code == 403


def test_owner_cannot_suspend(auth_client, reviewer_client, db_session):
    """Owner cannot suspend (platform reviewer only)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    resp = _suspend(auth_client, inst["id"])
    assert resp.status_code == 403


def test_platform_reviewer_cannot_edit_institution_through_patch(
    auth_client, reviewer_client, db_session
):
    """A platform reviewer (without institution membership) cannot PATCH
    the institution profile (owner/rep only). Reviewing is separate from
    profile editing."""
    inst = _create_institution(auth_client)
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}",
        json={"description": "Hijacked."},
    )
    assert resp.status_code == 403


def test_ordinary_membership_cannot_grant_platform_reviewer(
    auth_client, reviewer_client, db_session
):
    """A user with only institution memberships cannot verify because
    is_platform_reviewer is separate and defaults to False."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(auth_client, inst["id"])
    assert resp.status_code == 403


def test_client_cannot_turn_itself_into_platform_reviewer(client, db_session):
    """A client cannot set is_platform_reviewer through the request body.

    The registration schema has no is_platform_reviewer field, so any
    injected value is ignored. The user is created with the server-side
    default (is_platform_reviewer=False) — a client cannot self-elevate.
    """
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "hacker@aikyra.dev",
            "password": "password123",
            "full_name": "Hacker",
            "is_platform_reviewer": True,
            "is_active": True,
            "is_verified": True,
        },
    )
    # Registration succeeds but the injected fields are ignored.
    assert resp.status_code == 201

    # The created user must NOT be a platform reviewer (nor active/verified
    # via client input).
    user = db_session.query(User).filter(User.email == "hacker@aikyra.dev").first()
    assert user is not None
    assert user.is_platform_reviewer is False


def test_client_cannot_provide_verified_by(
    auth_client, reviewer_client, db_session
):
    """Client-supplied verified_by is rejected (422)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "verified_by": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


def test_client_cannot_provide_verified_at(
    auth_client, reviewer_client, db_session
):
    """Client-supplied verified_at is rejected (422)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "verified_at": "2026-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422


def test_client_cannot_provide_verification_status(
    auth_client, reviewer_client, db_session
):
    """Client-supplied verification_status is rejected (422)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "verification_status": "verified"},
    )
    assert resp.status_code == 422


def test_client_cannot_provide_reviewer_user_id(
    auth_client, reviewer_client, db_session
):
    """Client-supplied reviewer_user_id is rejected (422)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "reviewer_user_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


def test_invalid_action_rejected(auth_client):
    """Invalid action value -> 422."""
    inst = _create_institution(auth_client)
    resp = auth_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "bogus_action"},
    )
    assert resp.status_code == 422


def test_nonexistent_institution_returns_404(auth_client):
    """Verification on a nonexistent institution -> 404."""
    resp = _submit(auth_client, str(uuid.uuid4()))
    assert resp.status_code == 404


def test_full_happy_path(auth_client, reviewer_client, db_session):
    """Complete workflow: unverified -> pending -> verified -> suspended -> verified."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")

    resp = _submit(auth_client, inst["id"])
    assert resp.json()["verification_status"] == "pending_review"

    resp = _verify(reviewer_client, inst["id"], note="Approved.")
    assert resp.json()["verification_status"] == "verified"

    resp = _suspend(reviewer_client, inst["id"], note="Issue found.")
    assert resp.json()["verification_status"] == "suspended"

    resp = _reinstate(reviewer_client, inst["id"])
    assert resp.json()["verification_status"] == "verified"
    assert resp.json()["verified_by"] == str(reviewer_id)


# --- Non-platform-reviewer denial tests -----------------------------------------


def test_faculty_cannot_verify(auth_client, reviewer_client, db_session):
    """A faculty (or any institution member) without platform reviewer flag
    cannot verify. The owner (ordinary user) is used as the non-reviewer."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(auth_client, inst["id"])
    assert resp.status_code == 403


def test_student_cannot_verify(auth_client, reviewer_client, db_session):
    """A student (institution member) cannot verify."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(auth_client, inst["id"])
    assert resp.status_code == 403


def test_platform_reviewer_flag_isolated_from_membership(
    auth_client, reviewer_client, db_session
):
    """Verification authority comes from is_platform_reviewer alone, not
    from any institution membership."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "verified"
    assert resp.json()["verified_by"] == str(reviewer_id)

    # Ordinary owner cannot verify even though they own the institution
    inst2 = _create_institution(
        auth_client, name="Another University", website="https://another.example.com"
    )
    _submit(auth_client, inst2["id"])
    resp = _verify(auth_client, inst2["id"])
    assert resp.status_code == 403


def test_inactive_platform_reviewer_cannot_verify(
    auth_client, reviewer_client, db_session
):
    """An is_active=False platform reviewer cannot verify (rejected at auth)."""
    inst = _create_institution(auth_client)
    reviewer_user = (
        db_session.query(User).filter(User.email == "reviewer@aikyra.dev").first()
    )
    reviewer_user.is_active = False
    db_session.commit()

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 401
