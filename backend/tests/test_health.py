from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.main import app

Handler = Callable[[httpx.Request], httpx.Response]


def _override_client(handler: Handler):
    async def _client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    return _client


@pytest.fixture(autouse=True)
def _reset_dependencies() -> AsyncIterator[None]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        ollama_host="http://ollama.test",
        ollama_model="test-model",
    )
    yield
    app.dependency_overrides.clear()


def test_health_ok_when_ollama_reachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:7b-instruct"}]},
            request=request,
        )

    app.dependency_overrides[get_http_client] = _override_client(handler)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ollama"]["reachable"] is True
    assert data["ollama"]["model"] == "test-model"
    assert data["ollama"]["loaded_models"] == ["qwen2.5:7b-instruct"]


def test_health_degraded_when_ollama_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    app.dependency_overrides[get_http_client] = _override_client(handler)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["ollama"]["reachable"] is False
    assert "error" in data["ollama"]
