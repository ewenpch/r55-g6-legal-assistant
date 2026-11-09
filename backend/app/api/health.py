from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["health"])


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


@router.get("/health")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """État de l'API et de la configuration LLM (la clé n'est jamais exposée)."""
    configured = bool(settings.llm_api_key)
    return {
        "status": "ok" if configured else "degraded",
        "llm": {
            "configured": configured,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
        },
    }
