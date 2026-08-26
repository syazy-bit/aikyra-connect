from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotAuthenticatedError
from app.schemas.auth import (
    AuthLogin,
    AuthLoginResponse,
    AuthMeResponse,
    AuthRegister,
    AuthRegisterResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def _extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """Extract the Bearer token from the Authorization header.

    Raises NotAuthenticatedError if the header is missing or malformed.
    """
    if authorization is None:
        raise NotAuthenticatedError("Missing Authorization header.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise NotAuthenticatedError("Invalid Authorization header format.")
    token = parts[1].strip()
    if not token:
        raise NotAuthenticatedError("Missing Bearer token.")
    return token


def get_current_user(
    token: Annotated[str, Depends(_extract_bearer_token)],
    service: AuthService = Depends(get_auth_service),
):
    """FastAPI dependency: resolve the authenticated user from a Bearer token."""
    return service.resolve_current_user(token)


@router.post(
    "/register",
    response_model=AuthRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: AuthRegister,
    service: AuthService = Depends(get_auth_service),
) -> AuthRegisterResponse:
    """Register a new user account."""
    user = service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return AuthRegisterResponse.model_validate(user)


@router.post("/login", response_model=AuthLoginResponse)
def login_user(
    payload: AuthLogin,
    service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    """Authenticate and return a JWT access token."""
    token = service.login(email=payload.email, password=payload.password)
    return AuthLoginResponse(access_token=token)


@router.get("/me", response_model=AuthMeResponse)
def get_me(
    current_user: Annotated[object, Depends(get_current_user)],
) -> AuthMeResponse:
    """Return the currently authenticated user's profile."""
    return AuthMeResponse.model_validate(current_user)
