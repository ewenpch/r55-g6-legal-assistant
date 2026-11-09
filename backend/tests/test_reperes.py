import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services import reperes

PAGE_1 = (
    "Article 1 - Le bail est conclu pour trois ans à compter du 1er janvier 2026.\n"
    "Article 2 - Le loyer est de 1 250,50 € par mois, payable avant le 05/02/2026."
)
PAGE_2 = (
    "Article 3 - Le préavis est de 3 mois. Le dépôt de garantie est de 650 euros.\n"
    "Le preneur verse une caution."
)


def make_pdf() -> bytes:
    doc = pymupdf.open()
    for text in (PAGE_1, PAGE_2):
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(40, 40, 560, 400), text, fontsize=10)
    return doc.tobytes()


@pytest.fixture
def client(tmp_path):
    # Aucune clé d'API et aucun faux LLM : ces fonctions ne doivent jamais appeler le modèle.
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, llm_api_key="", database_path=tmp_path / "t.db"
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str = "a@b.fr") -> TestClient:
    client.post("/api/auth/register", json={"email": email, "password": "motdepasse1"})
    return client


def _upload(client: TestClient) -> int:
    files = {"file": ("bail.pdf", make_pdf(), "application/pdf")}
    return client.post("/api/documents", files=files).json()["id"]


def test_find_reperes_unit() -> None:
    found = reperes.find_reperes([PAGE_1, PAGE_2])

    assert {m["texte"] for m in found["montants"]} == {"1 250,50 €", "650 euros"}
    assert {d["texte"] for d in found["dates"]} == {"1er janvier 2026", "05/02/2026"}
    assert {(d["texte"], d["page"]) for d in found["durees"]} == {
        ("trois ans", 1),
        ("3 mois", 2),
    }
    terms = {t["terme"]: t["pages"] for t in found["termes"]}
    assert terms == {"préavis": [2], "dépôt de garantie": [2], "caution": [2], "preneur": [2]}


def test_find_reperes_has_page_and_context() -> None:
    montant = reperes.find_reperes([PAGE_1])["montants"][0]

    assert montant["page"] == 1
    assert "Le loyer est de" in montant["contexte"]


def test_search_unit() -> None:
    total, hits = reperes.search([PAGE_1, PAGE_2], "LOYER")

    assert total == 1
    assert hits[0]["page"] == 1
    assert "loyer" in hits[0]["extrait"].lower()
    assert reperes.search([PAGE_1], "introuvable") == (0, [])


def test_reperes_endpoint_works_without_llm(client) -> None:
    _login(client)
    doc_id = _upload(client)

    response = client.get(f"/api/documents/{doc_id}/reperes")

    assert response.status_code == 200
    data = response.json()
    assert any(m["texte"] == "650 euros" and m["page"] == 2 for m in data["montants"])
    assert any(t["terme"] == "préavis" for t in data["termes"])


def test_search_endpoint_works_without_llm(client) -> None:
    _login(client)
    doc_id = _upload(client)

    data = client.get(f"/api/documents/{doc_id}/search", params={"q": "préavis"}).json()

    assert data["total"] == 1
    assert data["resultats"][0]["page"] == 2


def test_search_rejects_too_short_query(client) -> None:
    _login(client)
    doc_id = _upload(client)

    assert client.get(f"/api/documents/{doc_id}/search", params={"q": "a"}).status_code == 422


def test_tools_are_private_and_protected(client, tmp_path) -> None:
    _login(client, "alice@x.fr")
    doc_id = _upload(client)

    with TestClient(app) as bob, TestClient(app) as anon:
        _login(bob, "bob@x.fr")
        for path in (f"/api/documents/{doc_id}/reperes", f"/api/documents/{doc_id}/search?q=loyer"):
            assert bob.get(path).status_code == 404
            assert anon.get(path).status_code == 401
