import sqlite3
from collections.abc import AsyncIterator

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.main import app

CONTENT = '{"en_clair": "Explication.", "a_retenir": ["Point"]}'
CLAUSE = "Le preneur paie le loyer le 5."
STATE = {"status": 200}  # statut renvoyé par le faux LLM


def make_pdf(pages: int = 1, text: str = "Le preneur s'engage à payer le loyer mensuel.") -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    return doc.tobytes()


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_api_key="gsk_secret", llm_model="m", database_path=path
    )
    STATE["status"] = 200

    def handler(request: httpx.Request) -> httpx.Response:
        if STATE["status"] != 200:
            return httpx.Response(STATE["status"], json={"error": "x"}, request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": CONTENT}}]})

    async def _client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    app.dependency_overrides[get_http_client] = _client
    yield path
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str = "a@b.fr") -> TestClient:
    client.post("/api/auth/register", json={"email": email, "password": "motdepasse1"})
    return client


def _upload(client: TestClient, data: bytes, name: str = "contrat.pdf"):
    return client.post("/api/documents", files={"file": (name, data, "application/pdf")})


# --- 5.6 journal des appels au LLM -------------------------------------------------


def test_llm_call_is_logged(db_path) -> None:
    with TestClient(app) as client:
        _login(client)
        assert client.get("/api/llm-logs").json() == []
        client.post("/api/explain", json={"text": CLAUSE})
        logs = client.get("/api/llm-logs").json()

    assert len(logs) == 1
    log = logs[0]
    assert log["request"] == CLAUSE
    assert "Explication." in log["response"]
    assert log["error"] is None
    assert log["model"] == "m"
    assert log["duration_ms"] >= 0
    assert "gsk_secret" not in str(logs)


def test_failed_llm_call_is_logged_with_error(db_path) -> None:
    STATE["status"] = 429
    with TestClient(app) as client:
        _login(client)
        assert client.post("/api/explain", json={"text": CLAUSE}).status_code == 429
        log = client.get("/api/llm-logs").json()[0]

    assert log["response"] is None
    assert "Trop de requêtes" in log["error"]


def test_logs_are_private_and_protected(db_path) -> None:
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anon:
        _login(alice, "alice@x.fr")
        _login(bob, "bob@x.fr")
        alice.post("/api/explain", json={"text": CLAUSE})

        assert len(alice.get("/api/llm-logs").json()) == 1
        assert bob.get("/api/llm-logs").json() == []
        assert anon.get("/api/llm-logs").status_code == 401


# --- 5.7 dépôt de fichier ------------------------------------------------------------


def test_upload_pdf_is_received_and_kept(db_path) -> None:
    with TestClient(app) as client:
        _login(client)
        response = _upload(client, make_pdf(2))
        assert response.status_code == 201
        meta = response.json()
        assert meta["filename"] == "contrat.pdf"
        assert meta["pages"] == 2

        assert [d["id"] for d in client.get("/api/documents").json()] == [meta["id"]]
        detail = client.get(f"/api/documents/{meta['id']}").json()
        assert "loyer mensuel" in detail["text"]

    stored = sqlite3.connect(db_path).execute("SELECT length(content) FROM documents").fetchone()
    assert stored[0] == meta["size"]


@pytest.mark.parametrize(
    ("name", "data", "status", "message"),
    [
        ("contrat.txt", b"%PDF-1.4 x", 400, ".pdf"),
        ("contrat.pdf", b"ceci n'est pas un pdf", 400, "vrai PDF"),
        ("contrat.pdf", b"%PDF-1.4 corrompu", 400, "illisible"),
        ("contrat.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024), 413, "5 Mo"),
    ],
)
def test_upload_rejects_bad_files(db_path, name, data, status, message) -> None:
    with TestClient(app) as client:
        _login(client)
        response = _upload(client, data, name)

    assert response.status_code == status
    assert message in response.json()["detail"]


def test_upload_rejects_too_many_pages_and_scans(db_path) -> None:
    with TestClient(app) as client:
        _login(client)
        too_long = _upload(client, make_pdf(11))
        scan = _upload(client, make_pdf(1, text=""))

    assert too_long.status_code == 422
    assert "11 pages" in too_long.json()["detail"]
    assert scan.status_code == 422
    assert "Aucun texte" in scan.json()["detail"]


def test_documents_are_private_and_protected(db_path) -> None:
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anon:
        _login(alice, "alice@x.fr")
        _login(bob, "bob@x.fr")
        doc_id = _upload(alice, make_pdf()).json()["id"]

        assert bob.get("/api/documents").json() == []
        assert bob.get(f"/api/documents/{doc_id}").status_code == 404
        assert bob.delete(f"/api/documents/{doc_id}").status_code == 404
        assert anon.get("/api/documents").status_code == 401
        assert _upload(anon, make_pdf()).status_code == 401

        assert alice.delete(f"/api/documents/{doc_id}").status_code == 204
        assert alice.get("/api/documents").json() == []
