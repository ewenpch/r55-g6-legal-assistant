"""Dépôt de PDF : validation, extraction du texte page par page, conservation par utilisateur."""

import pymupdf
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.auth import CurrentUser
from app.db import Db

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MIN_TEXT_CHARS = 20


class DocumentSummary(BaseModel):
    id: int
    filename: str
    size: int
    pages: int
    created_at: str


class DocumentDetail(DocumentSummary):
    text: str


def _extract_text(data: bytes) -> tuple[int, str]:
    """Renvoie (nombre de pages, texte) ou lève une HTTPException au message distinct."""
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Ce fichier n'est pas un vrai PDF.")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Ce PDF est illisible ou corrompu.") from None
    with doc:
        if doc.needs_pass:
            raise HTTPException(status_code=400, detail="Ce PDF est protégé par un mot de passe.")
        if doc.page_count > MAX_PAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Ce PDF a {doc.page_count} pages ({MAX_PAGES} maximum).",
            )
        text = "\n\n".join(page.get_text().strip() for page in doc).strip()
        pages = doc.page_count
    if len(text) < MIN_TEXT_CHARS:
        raise HTTPException(
            status_code=422,
            detail="Aucun texte extractible : ce PDF est peut-être un scan.",
        )
    return pages, text


@router.post("", status_code=201)
async def upload(file: UploadFile, user: CurrentUser, db: Db) -> DocumentSummary:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .pdf sont acceptés.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Le fichier dépasse 5 Mo.")
    pages, text = _extract_text(data)
    cursor = db.execute(
        "INSERT INTO documents (user_id, filename, size, pages, text, content)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user.id, filename[:200], len(data), pages, text, data),
    )
    row = db.execute(
        "SELECT id, filename, size, pages, created_at FROM documents WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return DocumentSummary(**dict(row))


@router.get("")
def list_documents(user: CurrentUser, db: Db) -> list[DocumentSummary]:
    rows = db.execute(
        "SELECT id, filename, size, pages, created_at FROM documents"
        " WHERE user_id = ? ORDER BY id DESC",
        (user.id,),
    ).fetchall()
    return [DocumentSummary(**dict(row)) for row in rows]


@router.get("/{document_id}")
def get_document(document_id: int, user: CurrentUser, db: Db) -> DocumentDetail:
    row = db.execute(
        "SELECT id, filename, size, pages, created_at, text FROM documents"
        " WHERE id = ? AND user_id = ?",
        (document_id, user.id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return DocumentDetail(**dict(row))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, user: CurrentUser, db: Db) -> None:
    cursor = db.execute(
        "DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user.id)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Document introuvable.")
