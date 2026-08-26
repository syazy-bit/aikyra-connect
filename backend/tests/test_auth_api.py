"""Phase 4C — Authentication API tests.

Covers: registration (validation, duplicates, password security), login
(valid credentials, invalid credentials, user enumeration prevention),
and GET /me (authenticated, unauthenticated, invalid/expired tokens).
"""

import uuid
from unittest.mock import patch

from jose import jwt
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings

VALID_PAYLOAD = {
    "email": "test@aikyra.dev",
    "password": "password123",
    "full_name": "Test User",
}


def _register(client, **overrides):
    payload = {**VALID_PAYLOAD, **overrides}
    response = client.post("/api/auth/register", json=payload)
    return response


def _login(client, email="test@aikyra.dev", password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _register_and_login(client, **register_overrides):
    reg = _register(client, **register_overrides)
    assert reg.status_code == 201
    login_resp = _login(
        client,
        email=register_overrides.get("email", VALID_PAYLOAD["email"]),
        password=register_overrides.get("password", VALID_PAYLOAD["password"]),
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# --- Registration -------------------------------------------------------------


def test_register_success(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_PAYLOAD["email"]
    assert body["full_name"] == VALID_PAYLOAD["full_name"]
    uuid.UUID(body["id"])
    assert body["created_at"]


def test_register_returns_user_fields(client):
    body = _register(client).json()
    assert set(body.keys()) == {"id", "email", "full_name", "created_at"}


def test_register_email_normalized_to_lowercase(client):
    response = _register(client, email="TEST@AIKYRA.DEV")
    assert response.status_code == 201
    assert response.json()["email"] == "test@aikyra.dev"


def test_register_duplicate_email(client):
    _register(client)
    response = _register(client)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_duplicate_email_case_insensitive(client):
    _register(client)
    response = _register(client, email="Test@Aikyra.Dev")
    assert response.status_code == 409


def test_register_invalid_email(client):
    for bad in ("plainaddress", "missing@tld", "@no-local.com", "user@", "x"):
        response = _register(client, email=bad)
        assert response.status_code == 422, f"Expected 422 for email: {bad}"


def test_register_short_password(client):
    response = _register(client, password="short")
    assert response.status_code == 422


def test_register_password_exactly_8_chars(client):
    response = _register(client, password="12345678")
    assert response.status_code == 201


def test_register_password_exactly_7_chars_rejected(client):
    response = _register(client, password="1234567")
    assert response.status_code == 422


def test_register_long_password(client):
    response = _register(client, password="x" * 129)
    assert response.status_code == 422


def test_register_password_exactly_128_chars(client):
    response = _register(client, password="x" * 128)
    assert response.status_code == 201


def test_register_missing_password(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "password"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_missing_email(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_optional_full_name(client):
    response = _register(client, full_name=None)
    assert response.status_code == 201
    assert response.json()["full_name"] is None


def test_password_not_in_response(client):
    body = _register(client).json()
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_empty_body(client):
    response = client.post("/api/auth/register", json={})
    assert response.status_code == 422


def test_register_concurrent_race_returns_409(client, db_session):
    """When a concurrent insert triggers an IntegrityError, the API returns 409."""
    _register(client, email="race@aikyra.dev")

    # Simulate a race: the service's pre-check finds no duplicate, but the
    # INSERT violates the unique lower(email) index (a concurrent transaction
    # inserted the same email between the check and the commit).
    from app.models.user import User

    original_get_by_email = __import__(
        "app.repositories.user_repository", fromlist=["UserRepository"]
    ).UserRepository.get_by_email

    call_count = 0

    def _race_get_by_email(self, email):
        nonlocal call_count
        call_count += 1
        # Let the pre-check pass (returns None), but the real constraint
        # violation will be raised by the DB on commit.
        if call_count == 2:
            # Second call is from the concurrent register attempt — return
            # None so the service proceeds to INSERT.
            return None
        return original_get_by_email(self, email)

    def _raise_integrity_error(*args, **kwargs):
        raise IntegrityError("INSERT", "params", Exception("duplicate key"))

    with patch(
        "app.services.auth_service.UserRepository.get_by_email",
        _race_get_by_email,
    ), patch(
        "app.services.auth_service.AuthService._commit",
        _raise_integrity_error,
    ):
        response = _register(client, email="race@aikyra.dev")
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


# --- Login --------------------------------------------------------------------


def test_login_success(client):
    _register(client)
    response = _login(client)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_returns_valid_jwt(client):
    _register(client)
    token = _login(client).json()["access_token"]
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] is not None
    uuid.UUID(payload["sub"])
    assert "exp" in payload
    assert "iat" in payload


def test_login_wrong_password(client):
    _register(client)
    response = _login(client, password="wrongpassword")
    assert response.status_code == 401


def test_login_nonexistent_email(client):
    response = _login(client, email="nobody@aikyra.dev")
    assert response.status_code == 401


def test_login_prevents_user_enumeration(client):
    """Both wrong-email and wrong-password must return the same error."""
    _register(client)
    wrong_email = _login(client, email="nobody@aikyra.dev")
    wrong_password = _login(client, password="wrongpassword")
    assert wrong_email.json() == wrong_password.json()


def test_login_inactive_user_rejected(client, db_session):
    """An inactive user must not be able to log in."""
    _register(client, email="inactive@aikyra.dev")
    # Directly deactivate via test DB session
    from app.models.user import User
    from sqlalchemy import func

    user = db_session.execute(
        __import__("sqlalchemy").select(User).where(
            func.lower(User.email) == "inactive@aikyra.dev"
        )
    ).scalar_one()
    user.is_active = False
    db_session.commit()

    response = _login(client, email="inactive@aikyra.dev", password="password123")
    assert response.status_code == 401


def test_login_empty_body(client):
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 422


def test_login_long_password_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "user@aikyra.dev", "password": "x" * 129},
    )
    assert response.status_code == 422


# --- GET /me ------------------------------------------------------------------


def test_me_authenticated(client):
    token = _register_and_login(client)
    response = client.get("/api/auth/me", headers=_auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == VALID_PAYLOAD["email"]
    assert body["full_name"] == VALID_PAYLOAD["full_name"]
    assert body["is_active"] is True
    uuid.UUID(body["id"])
    assert body["created_at"]


def test_me_no_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401


def test_me_expired_token(client):
    settings = get_settings()
    _register(client)
    # Create a token that expired 1 hour ago using integer timestamps
    import time

    expired_payload = {
        "sub": str(uuid.uuid4()),
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    response = client.get(
        "/api/auth/me", headers=_auth_header(expired_token)
    )
    assert response.status_code == 401


def test_me_malformed_header(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "NotBearer token"}
    )
    assert response.status_code == 401


def test_me_empty_bearer_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer "}
    )
    assert response.status_code == 401


def test_me_nonexistent_user(client):
    """A token referencing a deleted/nonexistent user must be rejected."""
    import time

    settings = get_settings()
    fake_payload = {
        "sub": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 1800,
    }
    fake_token = jwt.encode(
        fake_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    response = client.get("/api/auth/me", headers=_auth_header(fake_token))
    assert response.status_code == 401


# --- Phase 1–3 backward compatibility ----------------------------------------


def test_health_endpoint_unaffected(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_challenge_endpoints_unaffected(client):
    """Challenge CRUD still works without authentication."""
    challenge_payload = {
        "title": "Borewells failing in drought village",
        "description": "400 farming families lose crops every summer.",
        "location": "Anantapur, Andhra Pradesh",
    }
    created = client.post("/api/challenges", json=challenge_payload)
    assert created.status_code == 201

    listed = client.get("/api/challenges")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_institution_endpoints_unaffected(client, auth_client):
    """Institution CRUD works with auth (Checkpoint 2) and reads remain public."""
    institution_payload = {
        "name": "Regional Institute of Technology",
        "institution_type": "university",
        "location": "Anantapur, Andhra Pradesh",
    }
    created = auth_client.post("/api/institutions", json=institution_payload)
    assert created.status_code == 201

    listed = client.get("/api/institutions")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    get_one = client.get(f"/api/institutions/{created.json()['id']}")
    assert get_one.status_code == 200

    unauthed = client.post("/api/institutions", json=institution_payload)
    assert unauthed.status_code == 401
