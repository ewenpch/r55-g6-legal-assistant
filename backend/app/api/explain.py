import json
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
HISTORY_LIMIT = 20


class ExplainRequest(BaseModel):
    text: str

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


class HistoryItem(ExplainResponse):
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
    try:
        result = await explain_clause(client, settings, body.text)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    db.execute(
        "INSERT INTO explanations (user_id, clause, en_clair, a_retenir) VALUES (?, ?, ?, ?)",
        (user.id, body.text, result.en_clair, json.dumps(result.a_retenir, ensure_ascii=False)),
    )
    return ExplainResponse(en_clair=result.en_clair, a_retenir=result.a_retenir)


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
