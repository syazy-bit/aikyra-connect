from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.challenges import router as challenges_router
from app.api.institutions import router as institutions_router
from app.api.matches import router as matches_router
from app.api.problem_dna import router as problem_dna_router
from app.api.related import router as related_router
from app.api.taxonomy import router as taxonomy_router
from app.core.exceptions import ConflictError, NotFoundError

app = FastAPI(
    title="Aikyra API",
    description="Collaborative societal innovation platform — REST API",
    version="0.2.0",
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


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(challenges_router)
app.include_router(problem_dna_router)
app.include_router(related_router)
app.include_router(taxonomy_router)
app.include_router(institutions_router)
app.include_router(matches_router)
