import json
from collections.abc import AsyncIterator

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.main import app

CLAUSE_3 = "Article 3 - Le preneur paie le loyer avant le 5 de chaque mois."
SEEN: list[dict] = []
REPLY = {"extrait": CLAUSE_3}


def make_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Article 2 - Le bail dure trois ans.")
    page.insert_text((72, 100), CLAUSE_3)
    return doc.tobytes()


@pytest.fixture(autouse=True)
def _setup(tmp_path):
    SEEN.clear()
    REPLY["extrait"] = CLAUSE_3
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_api_key="k", database_path=tmp_path / "t.db"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        SEEN.append(json.loads(request.content))
        content = json.dumps(
            {
                "en_clair": "Vous payez avant le 5.",
                "a_retenir": ["Date"],
                "extrait": REPLY["extrait"],
            }
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def _client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    app.dependency_overrides[get_http_client] = _client
    yield
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str = "a@b.fr") -> TestClient:
    client.post("/api/auth/register", json={"email": email, "password": "motdepasse1"})
    return client


def _upload(client: TestClient) -> int:
    files = {"file": ("bail.pdf", make_pdf(), "application/pdf")}
    return client.post("/api/documents", files=files).json()["id"]


def test_ask_about_a_clause_of_the_document() -> None:
    with TestClient(app) as client:
        _login(client)
        doc_id = _upload(client)
        response = client.post(
            "/api/explain", json={"text": "Explique la clause 3", "document_id": doc_id}
        )

    assert response.status_code == 200
    assert response.json()["en_clair"] == "Vous payez avant le 5."
    assert response.json()["extrait"] == CLAUSE_3
    user_message = SEEN[0]["messages"][1]["content"]
    assert "<document>" in user_message
    assert "Article 2 - Le bail dure trois ans." in user_message
    assert "<demande>\nExplique la clause 3\n</demande>" in user_message


def test_invented_quote_is_discarded() -> None:
    REPLY["extrait"] = "Article 3 - Le loyer est gratuit."

    with TestClient(app) as client:
        _login(client)
        doc_id = _upload(client)
        response = client.post(
            "/api/explain", json={"text": "Explique la clause 3", "document_id": doc_id}
        )

    assert response.status_code == 200
    assert response.json()["extrait"] == ""


def test_quote_check_ignores_whitespace_and_case() -> None:
    REPLY["extrait"] = "ARTICLE 3  -  le preneur paie\nle loyer avant le 5 de chaque mois."

    with TestClient(app) as client:
        _login(client)
        doc_id = _upload(client)
        response = client.post("/api/explain", json={"text": "clause 3", "document_id": doc_id})

    assert response.json()["extrait"] != ""


def test_without_document_the_clause_mode_is_unchanged() -> None:
    with TestClient(app) as client:
        _login(client)
        response = client.post("/api/explain", json={"text": "Le loyer est dû le 5."})

    assert response.json()["extrait"] == ""
    assert SEEN[0]["messages"][1]["content"].startswith("<clause>")


def test_other_users_document_is_not_reachable() -> None:
    with TestClient(app) as alice, TestClient(app) as bob:
        _login(alice, "alice@x.fr")
        _login(bob, "bob@x.fr")
        doc_id = _upload(alice)
        response = bob.post("/api/explain", json={"text": "clause 3", "document_id": doc_id})

    assert response.status_code == 404
    assert SEEN == []


def test_unknown_document_and_log_does_not_contain_whole_document() -> None:
    with TestClient(app) as client:
        _login(client)
        assert (
            client.post("/api/explain", json={"text": "x", "document_id": 999}).status_code == 404
        )
        doc_id = _upload(client)
        client.post("/api/explain", json={"text": "Explique la clause 3", "document_id": doc_id})
        log = client.get("/api/llm-logs").json()[0]

    assert log["request"] == "[bail.pdf] Explique la clause 3"
