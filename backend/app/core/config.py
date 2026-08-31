import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent

# Railway sets this to a truthy value (e.g. "production", "preview") for every
# deployment. It is the canonical signal that we are running in the cloud and
# therefore require a production JWT secret. Absent locally, local development
# is allowed to fall back to the shared dev secret.
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "")

# The in-repo development fallback. It is used ONLY for local development when
# JWT_SECRET_KEY is not provided. It is never an accepted value in a deployed
# environment (see Settings.__init__ below).
_DEV_JWT_SECRET = "dev-secret-change-in-production"


def _load_env_files() -> None:
    # backend/.env takes precedence over the repo root .env.
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")


_load_env_files()


class Settings:
    """Runtime configuration read from environment variables."""

    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.app_name: str = "Aikyra API"
        # Frontend origin for CORS. In production the deployed Vercel URL is
        # provided via FRONTEND_URL. When absent, only localhost/dev origins
        # are allowed (see main.py).
        self.frontend_url: str = os.getenv("FRONTEND_URL", "")
        # JWT authentication (Phase 4C)
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
        if not self.jwt_secret_key:
            if RAILWAY_ENVIRONMENT:
                # Deployed but no secret configured: fail fast instead of
                # silently signing tokens with the known development key.
                raise RuntimeError(
                    "JWT_SECRET_KEY is required in the deployment environment "
                    "(Railway). Generate a strong random secret and set it as a "
                    "Railway service variable before deploying."
                )
            # Local development only: the shared dev secret keeps local auth
            # working without configuration. Never accepted in production.
            self.jwt_secret_key = _DEV_JWT_SECRET
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
        # DEMO_MODE=true exposes the demo-only funding contribution endpoint
        # for the hackathon presentation. Default off.
        self.demo_mode: bool = os.getenv("DEMO_MODE", "").lower() == "true"
        # Local filesystem root for uploaded evidence (photo attachments).
        # Overridable via UPLOADS_DIR for tests/staging. Never served statically.
        self.uploads_dir: Path = Path(
            os.getenv("UPLOADS_DIR", str(BACKEND_DIR / "uploads"))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and configure it."
        )
    # Railway provides PostgreSQL connection strings with the legacy
    # `postgres://` scheme, but SQLAlchemy 2.0.36 requires `postgresql://`
    # (the `postgres` dialect name no longer exists). Normalize it safely so a
    # Railway DATABASE_URL works without altering standard `postgresql://` URLs.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url
