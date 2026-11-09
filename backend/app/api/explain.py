import json
import sqlite3
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.api.auth import CurrentUser
from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.db import Db
from app.services.llm import LLMError, explain_clause

router = APIRouter(prefix="/api", tags=["explain"])

MAX_CHARS = 4000
MAX_DOCUMENT_CHARS = 60_000


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


HISTORY_LIMIT = 20


class ExplainRequest(BaseModel):
    text: str
    document_id: int | None = None

    @field_validator("text")
    @classmethod
    def _check_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Collez une clause à expliquer.")
        if len(value) > MAX_CHARS:
            raise ValueError(f"Le texte est trop long ({MAX_CHARS} caractères maximum).")
        return value


class ExplainResponse(BaseModel):
    en_clair: str
    a_retenir: list[str]
    extrait: str = ""


class LogItem(BaseModel):
    id: int
    model: str
    request: str
    response: str | None
    error: str | None
    duration_ms: int
    created_at: str


def _log_call(
    db: sqlite3.Connection,
    user_id: int,
    model: str,
    request: str,
    response: str | None,
    error: str | None,
    started: float,
) -> None:
    """Journal des appels au LLM : demande, réponse, durée, erreur éventuelle (jamais la clé)."""
    duration_ms = round((time.perf_counter() - started) * 1000)
    db.execute(
        "INSERT INTO llm_logs (user_id, model, request, response, error, duration_ms)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, model, request, response, error, duration_ms),
    )
    db.commit()


class HistoryItem(BaseModel):
    en_clair: str
    a_retenir: list[str]
    id: int
    clause: str
    created_at: str


@router.post("/explain")
async def explain(
    body: ExplainRequest,
    user: CurrentUser,
    db: Db,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExplainResponse:
    document_text: str | None = None
    label = body.text
    if body.document_id is not None:
        row = db.execute(
            "SELECT filename, text FROM documents WHERE id = ? AND user_id = ?",
            (body.document_id, user.id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Document introuvable.")
        if len(row["text"]) > MAX_DOCUMENT_CHARS:
            raise HTTPException(
                status_code=422, detail="Ce document est trop long pour être analysé."
            )
        document_text = row["text"]
        # le document entier n'est pas rejoué dans le journal
        label = f"[{row['filename']}] {body.text}"

    started = time.perf_counter()
    try:
        result = await explain_clause(client, settings, body.text, document_text)
    except LLMError as exc:
        _log_call(db, user.id, settings.llm_model, label, None, exc.message, started)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None

    # Vérification de la citation : un extrait absent du document est écarté.
    extrait = result.extrait.strip()
    if document_text is None or _normalize(extrait) not in _normalize(document_text):
        extrait = ""
    _log_call(db, user.id, settings.llm_model, label, result.model_dump_json(), None, started)
    db.execute(
        "INSERT INTO explanations (user_id, clause, en_clair, a_retenir) VALUES (?, ?, ?, ?)",
        (user.id, label, result.en_clair, json.dumps(result.a_retenir, ensure_ascii=False)),
    )
    return ExplainResponse(en_clair=result.en_clair, a_retenir=result.a_retenir, extrait=extrait)


@router.get("/history")
def history(user: CurrentUser, db: Db) -> list[HistoryItem]:
    """Historique de l'utilisateur connecté uniquement (filtré par user_id)."""
    rows = db.execute(
        "SELECT id, clause, en_clair, a_retenir, created_at FROM explanations"
        " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user.id, HISTORY_LIMIT),
    ).fetchall()
    return [
        HistoryItem(
            id=r["id"],
            clause=r["clause"],
            en_clair=r["en_clair"],
            a_retenir=json.loads(r["a_retenir"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/llm-logs")
def llm_logs(user: CurrentUser, db: Db) -> list[LogItem]:
    """Journal des appels au LLM de l'utilisateur connecté uniquement."""
    rows = db.execute(
        "SELECT id, model, request, response, error, duration_ms, created_at FROM llm_logs"
        " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user.id, HISTORY_LIMIT),
    ).fetchall()
    return [LogItem(**dict(row)) for row in rows]
