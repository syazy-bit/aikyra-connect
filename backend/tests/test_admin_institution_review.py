"""Tests for Admin Portal Institution Review workflow."""

import uuid
from app.models.user import User


def _create_institution(c, **overrides):
    payload = {
        "name": f"Test Institution {uuid.uuid4().hex[:8]}",
        "institution_type": "university",
        "location": "Bengaluru, India",
        "website": "https://example.edu",
        "contact_email": "admin@example.edu",
        "domains": ["education"],
        "capabilities": {
            "departments": ["Computer Science", "Biomedical Engineering"],
            "expertise": ["AI Diagnostics", "Genome Sequencing"],
        },
        **overrides,
    }
    response = c.post("/api/institutions", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()


def _submit_for_review(c, institution_id):
    return c.patch(
        f"/api/institutions/{institution_id}/verification",
        json={"action": "submit_for_review"},
    )


# --- 1. Detail Endpoint Authorization & Retrieval ---


def test_admin_get_institution_requires_auth(client):
    """Unauthenticated access to admin institution detail returns 401."""
    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/admin/institutions/{random_id}")
    assert resp.status_code == 401


def test_admin_get_institution_requires_can_review_institutions(auth_client):
    """Standard user without can_review_institutions capability receives 403."""
    inst = _create_institution(auth_client)
    resp = auth_client.get(f"/api/admin/institutions/{inst['id']}")
    assert resp.status_code == 403


def test_admin_get_institution_success(auth_client, reviewer_client):
    """Admin with can_review_institutions can retrieve full institution review details."""
    inst = _create_institution(auth_client)
    resp = reviewer_client.get(f"/api/admin/institutions/{inst['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == inst["id"]
    assert data["name"] == inst["name"]
    assert data["location"] == "Bengaluru, India"
    assert data["institution_type"] == "university"
    assert data["website"] == "https://example.edu"
    assert data["contact_email"] == "admin@example.edu"
    assert data["verification_status"] == "unverified"
    assert "capabilities" in data
    assert "departments" in data["capabilities"]


def test_admin_get_institution_not_found(reviewer_client):
    """Admin requesting nonexistent institution returns 404."""
    random_id = str(uuid.uuid4())
    resp = reviewer_client.get(f"/api/admin/institutions/{random_id}")
    assert resp.status_code == 404


# --- 2. Verification State Machine Transitions via Admin ---


def test_admin_can_verify_institution(auth_client, reviewer_client):
    """Admin can verify an institution submitted for review."""
    inst = _create_institution(auth_client)
    # Submit for review
    submit_resp = _submit_for_review(auth_client, inst["id"])
    assert submit_resp.status_code == 200
    assert submit_resp.json()["verification_status"] == "pending_review"

    # Admin verifies
    verify_resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "note": "All credentials and domains verified."},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["verification_status"] == "verified"
    assert data["verification_note"] == "All credentials and domains verified."
    assert data["verified_at"] is not None
    assert data["verified_by"] is not None

    # Check detail via admin endpoint reflects updated state
    detail_resp = reviewer_client.get(f"/api/admin/institutions/{inst['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["verification_status"] == "verified"
    assert detail_resp.json()["verification_note"] == "All credentials and domains verified."


def test_admin_can_reject_institution(auth_client, reviewer_client):
    """Admin can reject an institution submitted for review."""
    inst = _create_institution(auth_client)
    _submit_for_review(auth_client, inst["id"])

    reject_resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "reject", "note": "Incomplete documentation submitted."},
    )
    assert reject_resp.status_code == 200
    data = reject_resp.json()
    assert data["verification_status"] == "rejected"
    assert data["verification_note"] == "Incomplete documentation submitted."
    assert data["verified_at"] is not None


def test_admin_can_suspend_and_reinstate_institution(auth_client, reviewer_client):
    """Admin can suspend a verified institution and later reinstate it."""
    inst = _create_institution(auth_client)
    _submit_for_review(auth_client, inst["id"])

    # 1. Verify
    reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify", "note": "Approved."},
    )

    # 2. Suspend
    suspend_resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "suspend", "note": "Suspended pending policy compliance review."},
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["verification_status"] == "suspended"
    assert suspend_resp.json()["verification_note"] == "Suspended pending policy compliance review."

    # 3. Reinstate
    reinstate_resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "reinstate", "note": "Compliance review cleared. Restored."},
    )
    assert reinstate_resp.status_code == 200
    assert reinstate_resp.json()["verification_status"] == "verified"
    assert reinstate_resp.json()["verification_note"] == "Compliance review cleared. Restored."


def test_unauthorized_user_cannot_perform_verification_actions(auth_client, reviewer_client):
    """Normal user without reviewer/admin capabilities cannot perform reviewer actions."""
    inst = _create_institution(auth_client)
    _submit_for_review(auth_client, inst["id"])

    # Regular auth_client attempts verify
    resp = auth_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "verify"},
    )
    assert resp.status_code == 403

    # Regular auth_client attempts suspend
    resp = auth_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "suspend"},
    )
    assert resp.status_code == 403


def test_invalid_state_transitions_rejected(auth_client, reviewer_client):
    """Invalid verification transitions according to the state machine return 409 Conflict."""
    inst = _create_institution(auth_client)
    # Initial status is unverified

    # Cannot suspend an unverified institution
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "suspend"},
    )
    assert resp.status_code == 409

    # Cannot reinstate an unverified institution
    resp = reviewer_client.patch(
        f"/api/institutions/{inst['id']}/verification",
        json={"action": "reinstate"},
    )
    assert resp.status_code == 409
