from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="r55-g6-legal-assistant API",
        version="0.1.0",
        description="Analyse de contrats assistee par une IA locale.",
    )
    app.include_router(health_router)
    return app


app = create_app()
