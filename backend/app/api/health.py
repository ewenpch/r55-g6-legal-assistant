from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["health"])

OLLAMA_TIMEOUT = 2.0


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


async def _check_ollama(client: httpx.AsyncClient, settings: Settings) -> dict[str, Any]:
    """Interroge Ollama et rapporte le modele reellement charge."""
    try:
        response = await client.get(f"{settings.ollama_host}/api/ps", timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {
            "reachable": False,
            "host": settings.ollama_host,
            "error": f"{type(exc).__name__}: {exc}".strip(),
        }

    loaded_models = [model.get("name", "") for model in response.json().get("models", [])]
    return {
        "reachable": True,
        "host": settings.ollama_host,
        "model": settings.ollama_model,
        "loaded_models": loaded_models,
    }


@router.get("/health")
async def health(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    ollama = await _check_ollama(client, settings)
    return {
        "status": "ok" if ollama["reachable"] else "degraded",
        "ollama": ollama,
    }
