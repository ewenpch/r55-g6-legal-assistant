from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.api.health import get_http_client
from app.config import Settings, get_settings
from app.services.llm import LLMError, explain_clause

router = APIRouter(prefix="/api", tags=["explain"])

MAX_CHARS = 4000


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
    answer: str


@router.post("/explain")
async def explain(
    body: ExplainRequest,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExplainResponse:
    try:
        return ExplainResponse(answer=await explain_clause(client, settings, body.text))
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
