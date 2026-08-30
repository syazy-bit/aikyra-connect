import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


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
        # JWT authentication (Phase 4C)
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
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
    return url
