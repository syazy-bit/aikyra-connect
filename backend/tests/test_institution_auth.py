"""Phase 4C Checkpoint 2 — Institution Authorization tests.

Covers: auth requirements on institution mutation endpoints, automatic owner
membership on creation, role-based PATCH access, public read access, membership
resolution from DB, and mass-assignment rejection.
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


# --- POST /api/institutions — auth required ------------------------------------


def test_create_institution_requires_auth(client):
    """Unauthenticated POST returns 401."""
    response = client.post("/api/institutions", json=MINIMAL_PAYLOAD)
    assert response.status_code == 401
    assert "Missing Authorization" in response.json()["detail"]


def test_create_institution_rejects_invalid_token(client):
    """POST with a malformed/invalid token returns 401."""
    response = client.post(
        "/api/institutions",
        json=MINIMAL_PAYLOAD,
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert response.status_code == 401


def test_create_institution_auto_creates_owner_membership(auth_client, db_session):
    """On successful creation the authenticated user is automatically added
    as an active owner via the institution_memberships table."""
    body = _create_institution(auth_client)
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "auth@aikyra.dev").first()
    membership = db_session.query(InstitutionMembership).filter(
        InstitutionMembership.user_id == user.id,
        InstitutionMembership.institution_id == uuid.UUID(body["id"]),
    ).first()

    assert membership is not None
    assert membership.role == InstitutionMembershipRole.OWNER
    assert membership.status == InstitutionMembershipStatus.ACTIVE


# --- PATCH /api/institutions/{id} — auth + role required -----------------------


def test_patch_requires_auth(client, auth_client):
    """Unauthenticated PATCH returns 401."""
    created = _create_institution(auth_client)
    response = client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "New text."},
    )
    assert response.status_code == 401


def test_patch_owner_can_update(auth_client):
    """The institution owner can PATCH the institution."""
    created = _create_institution(auth_client)
    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "Updated by owner."},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated by owner."


def test_patch_rep_can_update(auth_client, reviewer_client, db_session):
    """A user with an active representative membership can PATCH."""
    created = _create_institution(auth_client)
    from app.models.user import User

    rep_user = db_session.query(User).filter(User.email == "reviewer@aikyra.dev").first()
    _create_membership(
        db_session, rep_user.id, uuid.UUID(created["id"]), "representative"
    )
    response = reviewer_client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "Updated by rep."},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated by rep."


def test_patch_no_membership_forbidden(auth_client, reviewer_client, db_session):
    """A logged-in user without any membership gets 403."""
    created = _create_institution(auth_client)
    response = reviewer_client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "Hijack attempt."},
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_patch_reviewer_role_forbidden(auth_client, reviewer_client, db_session):
    """A platform reviewer (who is not an owner/rep member) cannot PATCH
    (write access is owner/rep only). The reviewer role is platform-level
    and does not grant institution write access."""
    created = _create_institution(auth_client)
    from app.models.user import User

    # reviewer_client is a platform reviewer with no owner/rep membership here
    response = reviewer_client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "Reviewer cannot write."},
    )
    assert response.status_code == 403


def test_patch_suspended_member_forbidden(auth_client, reviewer_client, db_session):
    """A suspended membership (even owner/rep role) is denied."""
    created = _create_institution(auth_client)
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "reviewer@aikyra.dev").first()
    _create_membership(
        db_session, user.id, uuid.UUID(created["id"]), "owner", status="suspended"
    )
    response = reviewer_client.patch(
        f"/api/institutions/{created['id']}",
        json={"description": "Suspended user tries."},
    )
    assert response.status_code == 403


def test_patch_other_institution_forbidden(auth_client, reviewer_client, db_session):
    """Owner of institution A cannot PATCH institution B."""
    from app.models.user import User

    created_a = _create_institution(auth_client, name="Institution A")
    # Create institution B as the reviewer user (different owner)
    created_b = _create_institution(reviewer_client, name="Institution B", website="https://b.example.com")
    response = auth_client.patch(
        f"/api/institutions/{created_b['id']}",
        json={"description": "Wrong institution."},
    )
    assert response.status_code == 403


# --- GET /api/institutions — public access -------------------------------------


def test_list_institutions_public(client):
    """Unauthenticated GET /api/institutions works."""
    response = client.get("/api/institutions")
    assert response.status_code == 200


def test_get_institution_public(client, auth_client):
    """Unauthenticated GET /api/institutions/{id} works."""
    created = _create_institution(auth_client)
    response = client.get(f"/api/institutions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


# --- GET /api/institutions/{id}/membership — auth required ---------------------


def test_get_membership_requires_auth(client, auth_client):
    """Unauthenticated membership check returns 401."""
    created = _create_institution(auth_client)
    response = client.get(f"/api/institutions/{created['id']}/membership")
    assert response.status_code == 401


def test_get_membership_returns_owner(auth_client, db_session):
    """The owner sees their membership details."""
    created = _create_institution(auth_client)
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "auth@aikyra.dev").first()
    response = auth_client.get(f"/api/institutions/{created['id']}/membership")
    body = response.json()
    assert body["is_member"] is True
    assert body["role"] == "owner"
    assert body["membership_status"] == "active"


def test_get_membership_returns_non_member(auth_client, reviewer_client, db_session):
    """A user with no membership on the institution sees is_member=False."""
    created = _create_institution(auth_client)
    response = reviewer_client.get(f"/api/institutions/{created['id']}/membership")
    body = response.json()
    assert body["is_member"] is False
    assert body["role"] is None
    assert body["membership_status"] is None


def test_get_membership_nonexistent_institution_returns_non_member(auth_client):
    """Membership check for a nonexistent institution returns is_member=False (200)."""
    response = auth_client.get(f"/api/institutions/{uuid.uuid4()}/membership")
    assert response.status_code == 200
    body = response.json()
    assert body["is_member"] is False


# --- Mass-assignment rejection -------------------------------------------------


def test_create_rejects_owner_id_injection(auth_client):
    """The owner_user_id field must not be injectable via the creation payload."""
    payload = {
        **MINIMAL_PAYLOAD,
        "owner_user_id": str(uuid.uuid4()),
    }
    response = auth_client.post("/api/institutions", json=payload)
    assert response.status_code == 422


def test_patch_rejects_role_injection(auth_client):
    """The PATCH schema (extra='forbid') must reject unknown fields."""
    created = _create_institution(auth_client)
    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={"role": "owner", "status": "verified"},
    )
    assert response.status_code == 422
