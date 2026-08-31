from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.challenges import router as challenges_router
from app.api.dashboard import router as dashboard_router
from app.api.institutions import router as institutions_router
from app.api.matches import router as matches_router
from app.api.organizations import router as organizations_router
from app.api.problem_dna import router as problem_dna_router
from app.api.proposals import router as proposals_router
from app.api.projects import router as projects_router
from app.api.related import router as related_router
from app.api.taxonomy import router as taxonomy_router
from app.api.teams import router as teams_router
from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    NotAuthenticatedError,
)

_settings = get_settings()

# CORS: the deployed Vercel frontend talks to this Railway backend, so its
# origin must be allowed. FRONTEND_URL is injected from the environment in
# production. Local development origins are always kept so the running Vite
# dev server can reach the API. Credentials are enabled only alongside an
# explicit origin list (never `"*"`), keeping the existing Bearer-token auth
# flow intact.
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if _settings.frontend_url:
    _allowed_origins.insert(0, _settings.frontend_url)

app = FastAPI(
    title="Aikyra API",
    description="Collaborative societal innovation platform — REST API",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


@app.exception_handler(NotAuthenticatedError)
def not_authenticated_handler(request: Request, exc: NotAuthenticatedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(ForbiddenError)
def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(challenges_router)
app.include_router(problem_dna_router)
app.include_router(related_router)
app.include_router(taxonomy_router)
app.include_router(institutions_router)
app.include_router(matches_router)
app.include_router(teams_router)
app.include_router(proposals_router)
app.include_router(projects_router)
app.include_router(organizations_router)
app.include_router(dashboard_router)
