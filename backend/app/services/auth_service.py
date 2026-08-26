"""Authentication service — registration, login, JWT, current-user resolution."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotAuthenticatedError
from app.models.user import User
from app.repositories.user_repository import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

_INVALID_CREDENTIALS = "Invalid email or password."


class AuthService:
    """Business logic for authentication.

    Owns transaction boundaries: repositories only flush; the service
    commits successful operations and rolls back on failure.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)

    # --- Registration ---------------------------------------------------

    def register(
        self, email: str, password: str, full_name: str | None = None
    ) -> User:
        """Create a new user account. Raises ConflictError on duplicate email."""
        existing = self.repository.get_by_email(email)
        if existing is not None:
            raise ConflictError(
                "An account with this email already exists."
            )
        try:
            user = self.repository.create(
                {
                    "email": email.lower(),
                    "hashed_password": pwd_context.hash(password),
                    "full_name": full_name,
                }
            )
            self._commit()
        except ConflictError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise ConflictError(
                "An account with this email already exists."
            )
        self.db.refresh(user)
        return user

    # --- Login ----------------------------------------------------------

    def login(self, email: str, password: str) -> str:
        """Authenticate and return a JWT access token.

        Always returns the same error message for both wrong-email and
        wrong-password to prevent user-enumeration.
        """
        user = self.repository.get_by_email(email)
        if user is None or not pwd_context.verify(password, user.hashed_password):
            raise NotAuthenticatedError(_INVALID_CREDENTIALS)
        if not user.is_active:
            raise NotAuthenticatedError(_INVALID_CREDENTIALS)
        return self.generate_token(user.id)

    # --- Token ----------------------------------------------------------

    def generate_token(self, user_id: UUID) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    # --- Current user resolution ----------------------------------------

    def resolve_current_user(self, token: str) -> User:
        """Decode a JWT and resolve the user. Raises NotAuthenticatedError on failure."""
        settings = get_settings()
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            user_id_str: str | None = payload.get("sub")
            if user_id_str is None:
                raise NotAuthenticatedError("Invalid authentication token.")
            user_id = UUID(user_id_str)
        except (JWTError, ValueError):
            raise NotAuthenticatedError("Invalid or expired authentication token.")

        user = self.repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise NotAuthenticatedError("Invalid or expired authentication token.")
        return user

    # --- Helpers --------------------------------------------------------

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
