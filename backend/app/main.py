from fastapi import FastAPI

app = FastAPI(
    title="Aikyra API",
    description="Collaborative societal innovation platform — REST API",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}
