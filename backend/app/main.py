from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.challenges import router as challenges_router
from app.core.exceptions import NotFoundError

app = FastAPI(
    title="Aikyra API",
    description="Collaborative societal innovation platform — REST API",
    version="0.1.0",
)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(challenges_router)
