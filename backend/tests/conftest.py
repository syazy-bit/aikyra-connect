import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
# backend/.env takes precedence over the repo root .env.
load_dotenv(BACKEND_DIR.parent / ".env")
load_dotenv(BACKEND_DIR / ".env")

from app.core.database import Base, get_db  # noqa: E402
import app.models.challenge  # noqa: F401,E402  # register models on Base.metadata
import app.models.institution  # noqa: F401,E402
import app.models.user  # noqa: F401,E402
import app.models.institution_membership  # noqa: F401,E402
from app.main import app  # noqa: E402


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        return url
    base = os.getenv("DATABASE_URL")
    if not base:
        raise RuntimeError(
            "Set TEST_DATABASE_URL or DATABASE_URL to run tests."
        )
    return f"{base.rsplit('/', 1)[0]}/aikyra_test"


TEST_DATABASE_URL = _test_database_url()
TEST_DB_NAME = TEST_DATABASE_URL.rsplit("/", 1)[1]


def _ensure_test_database_exists() -> None:
    """Create aikyra_test on the same server without touching the dev database."""
    admin_url = f"{TEST_DATABASE_URL.rsplit('/', 1)[0]}/postgres"
    admin_engine = create_engine(
        admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        admin_engine.dispose()


_ensure_test_database_exists()

test_engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_create_schema):
    yield
    with test_engine.begin() as conn:
        # Truncate in FK-dependency order: memberships depend on users and
        # institutions, so truncate memberships first.
        conn.execute(text('TRUNCATE TABLE "team_memberships" CASCADE'))
        conn.execute(text('TRUNCATE TABLE "teams" CASCADE'))
        conn.execute(text('TRUNCATE TABLE "institution_memberships" CASCADE'))
        conn.execute(text('TRUNCATE TABLE "users" CASCADE'))
        conn.execute(text('TRUNCATE TABLE "challenges" CASCADE'))
        conn.execute(text('TRUNCATE TABLE "institutions" CASCADE'))


@pytest.fixture
def db_session(_create_schema) -> Generator[Session, None, None]:
    """Provide a raw Session bound to the test database for direct DB manipulation."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header from a bearer token."""
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(c, email: str, password: str, full_name: str) -> str:
    """Register a user, log in, and return the bearer token."""
    c.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    login = c.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return login.json()["access_token"]


@pytest.fixture
def auth_client(db_session: Session):
    """Authenticated client: a registered + logged-in test user.

    Creates its own TestClient so it does not share headers with other
    auth fixtures.
    """
    from fastapi.testclient import TestClient

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    token = _register_and_login(c, "auth@aikyra.dev", "password123", "Auth Test User")
    c.headers.update(_auth_header(token))
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def reviewer_client(db_session: Session):
    """Authenticated client: a second registered + logged-in test user.

    Creates its own TestClient so it does not share headers with auth_client.
    """
    from fastapi.testclient import TestClient

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    token = _register_and_login(
        c, "reviewer@aikyra.dev", "password123", "Reviewer Test User"
    )
    c.headers.update(_auth_header(token))
    yield c
    app.dependency_overrides.clear()


# --- Helpers for team tests ----------------------------------------------------


def _create_institution(c, **overrides):
    """Create an institution via the API (returns JSON)."""
    payload = {
        "name": "Test Institution",
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
        "title": "Test Challenge",
        "description": "Test challenge description for team tests.",
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
        "name": "Test Team",
        "description": "Test team description.",
        **overrides,
    }
    response = c.post("/api/teams", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()
