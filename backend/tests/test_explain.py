from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.main import app

Handler = Callable[[httpx.Request], httpx.Response]
KEY = "gsk_secret"
CONTENT = '{"en_clair": "Vous payez le 5.", "a_retenir": ["Date : le 5"]}'
TEXT = "Le preneur s'engage à payer le loyer le 5 de chaque mois."


def _override_client(handler: Handler):
    async def _client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    return _client


def _no_call(request: httpx.Request) -> httpx.Response:
    pytest.fail("ne doit pas appeler le LLM")


@pytest.fixture(autouse=True)
def _setup(tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        llm_base_url="http://llm.test/v1",
        llm_api_key=KEY,
        llm_model="m",
        database_path=tmp_path / "test.db",
    )
    yield
    app.dependency_overrides.clear()


def _post(handler: Handler, text: str = TEXT):
    app.dependency_overrides[get_http_client] = _override_client(handler)
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"email": "a@b.fr", "password": "motdepasse1"})
        return client.post("/api/explain", json={"text": text})


def test_explain_success_sends_prompt_and_key() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(
            200, json={"choices": [{"message": {"content": CONTENT}}]}, request=request
        )

    response = _post(handler)

    assert response.status_code == 200
    assert response.json() == {"en_clair": "Vous payez le 5.", "a_retenir": ["Date : le 5"]}
    assert '"strict":true' in seen["body"].replace(" ", "")
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["url"] == "http://llm.test/v1/chat/completions"
    assert "<clause>" in seen["body"]


@pytest.mark.parametrize(("status", "expected"), [(401, 502), (429, 429), (500, 502)])
def test_explain_maps_http_errors(status: int, expected: int) -> None:
    response = _post(lambda r: httpx.Response(status, json={"error": "x"}, request=r))

    assert response.status_code == expected
    assert KEY not in response.text
    assert TEXT not in response.text
    assert response.json()["detail"]


def test_explain_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    response = _post(handler)

    assert response.status_code == 504
    assert "trop de temps" in response.json()["detail"]


def test_explain_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    assert _post(handler).status_code == 502


def test_explain_unexpected_payload() -> None:
    response = _post(lambda r: httpx.Response(200, json={"nope": 1}, request=r))

    assert response.status_code == 502


def test_explain_missing_key(tmp_path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, database_path=tmp_path / "test.db"
    )

    response = _post(_no_call)

    assert response.status_code == 503
    assert "clé" in response.json()["detail"]


@pytest.mark.parametrize("text", ["", "   \n "])
def test_explain_rejects_empty_input(text: str) -> None:
    assert _post(_no_call, text=text).status_code == 422


def test_explain_rejects_too_long_input() -> None:
    assert _post(_no_call, text="a" * 4001).status_code == 422


@pytest.mark.parametrize(
    "content",
    ["pas du json", '{"en_clair": "x"}', '{"en_clair": "x", "a_retenir": [], "extra": 1}'],
)
def test_explain_rejects_malformed_model_output(content: str) -> None:
    body = {"choices": [{"message": {"content": content}}]}

    response = _post(lambda r: httpx.Response(200, json=body, request=r))

    assert response.status_code == 502
    assert "mal formée" in response.json()["detail"]


def _json_failure(request: httpx.Request) -> httpx.Response:
    return httpx.Response(400, json={"error": {"code": "json_validate_failed"}}, request=request)


def test_explain_retries_on_json_generation_failure() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _json_failure(request)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": CONTENT}}]}, request=request
        )

    response = _post(handler)

    assert response.status_code == 200
    assert len(calls) == 2


def test_explain_gives_up_after_repeated_json_failures() -> None:
    response = _post(_json_failure)

    assert response.status_code == 502
    assert "réponse valide" in response.json()["detail"]
