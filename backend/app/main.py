from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.explain import router as explain_router
from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="r55-g6-legal-assistant API",
        version="0.1.0",
        description="Aide à la compréhension de contrats assistée par un LLM (Groq).",
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(explain_router)
    return app


app = create_app()
