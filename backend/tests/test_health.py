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


def test_empty_env_values_fall_back_to_defaults(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text("LLM_BASE_URL=\nLLM_API_KEY=\nLLM_MODEL=\n", encoding="utf-8")

    settings = Settings(_env_file=env)

    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_model == "openai/gpt-oss-20b"
