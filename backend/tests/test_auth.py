import sqlite3
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.main import app

PASSWORD = "motdepasse1"
CONTENT = '{"en_clair": "Explication.", "a_retenir": ["Point"]}'


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_api_key="k", database_path=path
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": CONTENT}}]})

    async def _client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    app.dependency_overrides[get_http_client] = _client
    yield path
    app.dependency_overrides.clear()


def _register(client: TestClient, email: str = "a@b.fr", password: str = PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_register_logs_in_and_hashes_password(db_path) -> None:
    with TestClient(app) as client:
        response = _register(client, "  A@B.fr ")
        assert response.status_code == 201
        assert response.json()["email"] == "a@b.fr"
        assert client.get("/api/auth/me").json()["email"] == "a@b.fr"

    stored = sqlite3.connect(db_path).execute("SELECT password_hash FROM users").fetchone()[0]
    assert PASSWORD not in stored
    assert stored.startswith("$2")  # bcrypt


def test_session_cookie_is_httponly_and_token_not_stored_raw(db_path) -> None:
    with TestClient(app) as client:
        response = _register(client)
        token = client.cookies.get("session")

    assert "httponly" in response.headers["set-cookie"].lower()
    rows = sqlite3.connect(db_path).execute("SELECT token_hash FROM sessions").fetchall()
    assert rows and token not in rows[0][0]


def test_register_duplicate_and_validation(db_path) -> None:
    with TestClient(app) as client:
        assert _register(client).status_code == 201
        assert _register(client).status_code == 409
        assert _register(client, "x@y.fr", "court").status_code == 422
        assert _register(client, "pas-un-email").status_code == 422
        assert _register(client, "z@y.fr", "é" * 40).status_code == 422  # > 72 octets


def test_login_logout_flow(db_path) -> None:
    with TestClient(app) as client:
        _register(client)
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/me").status_code == 401

        bad = client.post("/api/auth/login", json={"email": "a@b.fr", "password": "mauvais"})
        unknown = client.post("/api/auth/login", json={"email": "x@b.fr", "password": PASSWORD})
        assert bad.status_code == unknown.status_code == 401
        assert bad.json() == unknown.json()

        ok = client.post("/api/auth/login", json={"email": "a@b.fr", "password": PASSWORD})
        assert ok.status_code == 200
        assert client.get("/api/auth/me").status_code == 200


def test_logout_invalidates_session_server_side(db_path) -> None:
    with TestClient(app) as client:
        _register(client)
        token = client.cookies.get("session")
        client.post("/api/auth/logout")
        client.cookies.set("session", token)
        assert client.get("/api/auth/me").status_code == 401


def test_protected_routes_require_login(db_path) -> None:
    with TestClient(app) as client:
        assert client.get("/api/history").status_code == 401
        assert client.post("/api/explain", json={"text": "clause"}).status_code == 401


def test_history_is_private_to_each_user(db_path) -> None:
    with TestClient(app) as alice, TestClient(app) as bob:
        _register(alice, "alice@x.fr")
        _register(bob, "bob@x.fr")
        alice.post("/api/explain", json={"text": "clause secrète d'alice"})

        assert [i["clause"] for i in alice.get("/api/history").json()] == ["clause secrète d'alice"]
        assert bob.get("/api/history").json() == []
