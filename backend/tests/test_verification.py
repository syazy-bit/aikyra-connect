"""Phase 4C Checkpoint 3 — Verification Workflow tests.

Covers: verification state machine, authorization, security controls,
server-controlled fields, and invalid transition rejection.
"""

import uuid

from app.models.institution_membership import (
    InstitutionMembership,
    InstitutionMembershipRole,
    InstitutionMembershipStatus,
)

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
    from app.models.user import User
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


def test_submit_for_review_requires_membership(auth_client, reviewer_client, db_session):
    """Authenticated non-member gets 403."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    # reviewer has no membership on this institution
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_verify_by_reviewer(auth_client, reviewer_client, db_session):
    """Reviewer verifies a pending institution -> verified."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "verified"
    assert body["verified_by"] == str(reviewer_id)
    assert body["verified_at"] is not None


def test_owner_cannot_verify(auth_client, db_session):
    """Owner attempting verify gets 403 (wrong role)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _verify(auth_client, inst["id"])
    assert resp.status_code == 403


def test_reject_by_reviewer(auth_client, reviewer_client, db_session):
    """Reviewer rejects a pending institution -> rejected."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = _reject(reviewer_client, inst["id"], note="Needs more documentation.")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "rejected"
    assert body["verification_note"] == "Needs more documentation."


def test_resubmit_after_rejection(auth_client, reviewer_client, db_session):
    """Owner resubmits a rejected institution -> pending_review."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _reject(reviewer_client, inst["id"])

    resp = _resubmit(auth_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "pending_review"
    # Audit fields are cleared on resubmit.
    assert body["verified_by"] is None
    assert body["verified_at"] is None
    assert body["verification_note"] is None


def test_suspend_by_reviewer(auth_client, reviewer_client, db_session):
    """Reviewer suspends a verified institution -> suspended."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])

    resp = _suspend(reviewer_client, inst["id"], note="Policy violation.")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "suspended"
    assert body["verification_note"] == "Policy violation."


def test_reinstate_by_reviewer(auth_client, reviewer_client, db_session):
    """Reviewer reinstates a suspended institution -> verified."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    _suspend(reviewer_client, inst["id"])

    resp = _reinstate(reviewer_client, inst["id"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_status"] == "verified"


# --- Invalid transition tests ---------------------------------------------------


def test_invalid_transition_verified_to_unverified(auth_client, reviewer_client, db_session):
    """verified -> unverified is invalid."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])

    resp = auth_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "submit_for_review"},
    )
    assert resp.status_code == 409
    assert "Cannot perform" in resp.json()["detail"]


def test_invalid_transition_rejected_to_verified(auth_client, reviewer_client, db_session):
    """rejected -> verified directly is invalid."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _reject(reviewer_client, inst["id"])

    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 409


def test_submit_for_review_from_pending_only(auth_client, reviewer_client, db_session):
    """submit_for_review on already-pending institution -> 409."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])

    resp = _submit(auth_client, inst["id"])
    assert resp.status_code == 409


def test_invalid_transition_suspended_to_verify_directly(auth_client, reviewer_client, db_session):
    """suspended -> verify directly is invalid."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    _suspend(reviewer_client, inst["id"])

    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 409


# --- Audit field tests ----------------------------------------------------------


def test_verify_sets_verified_by_and_verified_at(auth_client, reviewer_client, db_session):
    """verify populates verified_by and verified_at."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    body = resp.json()
    assert body["verified_by"] == str(reviewer_id)
    assert body["verified_at"] is not None


def test_verify_sets_note(auth_client, reviewer_client, db_session):
    """verify persists the reviewer's note."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

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
    """User without membership on the institution -> 403."""
    inst = _create_institution(auth_client)
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_representative_can_submit(auth_client, reviewer_client, db_session):
    """A representative membership can submit for review."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(
        db_session, reviewer_id, uuid.UUID(inst["id"]), "representative"
    )
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "pending_review"


def test_reviewer_cannot_submit(auth_client, reviewer_client, db_session):
    """A reviewer membership cannot submit_for_review (owner/rep only)."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_owner_cannot_reject(auth_client, reviewer_client, db_session):
    """Owner cannot reject (reviewer only)."""
    inst = _create_institution(auth_client)
    _submit(auth_client, inst["id"])
    resp = _reject(auth_client, inst["id"])
    assert resp.status_code == 403


def test_owner_cannot_suspend(auth_client, reviewer_client, db_session):
    """Owner cannot suspend (reviewer only)."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")
    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])
    resp = _suspend(auth_client, inst["id"])
    assert resp.status_code == 403


def test_reviewer_cannot_edit_institution_through_patch(auth_client, reviewer_client, db_session):
    """Reviewer cannot use the normal PATCH endpoint (owner/rep only)."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}",
        json={"description": "Hijacked."},
    )
    assert resp.status_code == 403


def test_suspended_reviewer_membership_cannot_verify(auth_client, reviewer_client, db_session):
    """A suspended reviewer membership is denied."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(
        db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer", status="suspended"
    )
    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_invited_reviewer_membership_cannot_verify(auth_client, reviewer_client, db_session):
    """An invited (not active) reviewer membership is denied."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(
        db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer", status="invited"
    )
    _submit(auth_client, inst["id"])
    resp = _verify(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_suspended_owner_membership_cannot_submit(auth_client, reviewer_client, db_session):
    """A suspended owner membership cannot submit."""
    inst = _create_institution(auth_client)
    auth_id = _get_user_id(db_session, "auth@aikyra.dev")
    # auth_client already has an active owner membership from create_institution.
    # Add a suspended one — the active one from create_institution still exists,
    # so we need to test via a different user.
    # Instead, test via reviewer_client with a suspended owner membership.
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(
        db_session, reviewer_id, uuid.UUID(inst["id"]), "owner", status="suspended"
    )
    resp = _submit(reviewer_client, inst["id"])
    assert resp.status_code == 403


def test_client_cannot_provide_verified_by(auth_client, reviewer_client, db_session):
    """Client-supplied verified_by is rejected (extra='forbid')."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={
            "action": "verify",
            "verified_by": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


def test_client_cannot_provide_verified_at(auth_client, reviewer_client, db_session):
    """Client-supplied verified_at is rejected (extra='forbid')."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={
            "action": "verify",
            "verified_at": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422


def test_client_cannot_provide_verification_status(auth_client, reviewer_client, db_session):
    """Client-supplied verification_status is rejected (extra='forbid')."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={
            "action": "verify",
            "verification_status": "verified",
        },
    )
    assert resp.status_code == 422


def test_client_cannot_provide_reviewer_user_id(auth_client, reviewer_client, db_session):
    """Client-supplied reviewer_user_id is rejected (extra='forbid')."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={
            "action": "verify",
            "reviewer_user_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


def test_cannot_manipulate_another_institution_verification(auth_client, reviewer_client, db_session):
    """Reviewer cannot verify an institution they have no membership on."""
    inst_a = _create_institution(auth_client, name="Institution A")
    inst_b = _create_institution(
        reviewer_client, name="Institution B", website="https://b.example.com"
    )
    # reviewer is owner of B, not reviewer of A
    _submit(auth_client, inst_a["id"])
    resp = _verify(reviewer_client, inst_a["id"])
    assert resp.status_code == 403


def test_invalid_action_rejected(auth_client):
    """Invalid action value -> 422."""
    inst = _create_institution(auth_client)
    resp = auth_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "bogus_action"},
    )
    assert resp.status_code == 422


def test_invalid_state_transition_returns_409(auth_client, reviewer_client, db_session):
    """An invalid state transition returns 409 with descriptive message."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    _submit(auth_client, inst["id"])
    _verify(reviewer_client, inst["id"])

    # verified -> pending_review via submit_for_review is invalid
    resp = _submit(auth_client, inst["id"])
    assert resp.status_code == 409
    assert "Cannot perform" in resp.json()["detail"]


def test_nonexistent_institution_returns_404(auth_client):
    """Verification on nonexistent institution -> 404."""
    resp = _submit(auth_client, str(uuid.uuid4()))
    assert resp.status_code == 404


def test_full_happy_path(auth_client, reviewer_client, db_session):
    """Complete workflow: unverified -> pending -> verified -> suspended -> verified."""
    inst = _create_institution(auth_client)
    reviewer_id = _get_user_id(db_session, "reviewer@aikyra.dev")
    _create_membership(db_session, reviewer_id, uuid.UUID(inst["id"]), "reviewer")

    # Step 1: submit
    resp = _submit(auth_client, inst["id"])
    assert resp.json()["verification_status"] == "pending_review"

    # Step 2: verify
    resp = _verify(reviewer_client, inst["id"], note="Approved.")
    assert resp.json()["verification_status"] == "verified"

    # Step 3: suspend
    resp = _suspend(reviewer_client, inst["id"], note="Issue found.")
    assert resp.json()["verification_status"] == "suspended"

    # Step 4: reinstate
    resp = _reinstate(reviewer_client, inst["id"])
    assert resp.json()["verification_status"] == "verified"
    assert resp.json()["verified_by"] == str(reviewer_id)
