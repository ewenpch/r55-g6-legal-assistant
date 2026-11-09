import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _reset_dependencies():
    yield
    app.dependency_overrides.clear()


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, llm_model="test-model", **kwargs)


def test_health_ok_when_key_configured() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings(llm_api_key="gsk_secret")

    with TestClient(app) as client:
        response = client.get("/api/health")

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["llm"]["configured"] is True
    assert data["llm"]["model"] == "test-model"
    assert "gsk_secret" not in response.text


def test_health_degraded_without_key() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings()

    with TestClient(app) as client:
        data = client.get("/api/health").json()

    assert data["status"] == "degraded"
    assert data["llm"]["configured"] is False
