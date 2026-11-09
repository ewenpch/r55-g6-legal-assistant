"""Seul point d'appel au LLM (Groq, API compatible OpenAI), côté serveur uniquement."""

import json
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import BACKEND_DIR, Settings

PROMPT_PATH = BACKEND_DIR / "prompts" / "explain-clause.md"
LLM_TIMEOUT = 30.0
TEMPERATURE = 0.2
MAX_ATTEMPTS = 3


class ExplainResult(BaseModel):
    """Forme de la réponse du modèle, imposée par response_format (strict)."""

    model_config = ConfigDict(extra="forbid")

    en_clair: str
    a_retenir: list[str]
    extrait: str


RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "explication_clause",
        "strict": True,
        "schema": ExplainResult.model_json_schema(),
    },
}


class LLMError(Exception):
    """Erreur d'appel au LLM, avec un message lisible par l'utilisateur."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_system_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def _is_json_generation_failure(response: httpx.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        return response.json()["error"]["code"] == "json_validate_failed"
    except (ValueError, KeyError, TypeError):
        return False


def build_user_message(text: str, document: str | None = None) -> str:
    """Clause collée, ou demande + document, séparés par des balises (donnée, pas consigne)."""
    if document is None:
        return f"<clause>\n{text}\n</clause>"
    return f"<document>\n{document}\n</document>\n<demande>\n{text}\n</demande>"


async def explain_clause(
    client: httpx.AsyncClient, settings: Settings, text: str, document: str | None = None
) -> ExplainResult:
    """Envoie la clause (ou la demande + le document) au modèle ; renvoie l'explication structurée.

    Les messages d'erreur ne contiennent jamais la clé ni le texte de l'utilisateur.
    """
    if not settings.llm_api_key:
        raise LLMError("La clé d'API du LLM n'est pas configurée sur le serveur.", 503)

    payload = {
        "model": settings.llm_model,
        "temperature": TEMPERATURE,
        "response_format": RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": build_user_message(text, document)},
        ],
    }
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                timeout=LLM_TIMEOUT,
            )
        except httpx.TimeoutException:
            raise LLMError(
                "Le service d'IA a mis trop de temps à répondre. Réessayez.", 504
            ) from None
        except httpx.HTTPError:
            raise LLMError(
                "Impossible de joindre le service d'IA. Vérifiez la connexion."
            ) from None

        # Groq échoue parfois à produire un JSON valide : un nouvel essai suffit souvent.
        if _is_json_generation_failure(response) and attempt < MAX_ATTEMPTS - 1:
            continue
        break

    if response.status_code in (401, 403):
        raise LLMError("La clé d'API du LLM est refusée par le service d'IA.", 502)
    if response.status_code == 429:
        raise LLMError("Trop de requêtes vers le service d'IA. Réessayez dans un instant.", 429)
    if _is_json_generation_failure(response):
        raise LLMError("Le service d'IA n'a pas réussi à produire une réponse valide. Réessayez.")
    if response.status_code >= 400:
        raise LLMError(f"Le service d'IA a renvoyé une erreur ({response.status_code}).")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMError("Réponse inattendue du service d'IA.") from None
    if not isinstance(content, str) or not content.strip():
        raise LLMError("Le service d'IA a renvoyé une réponse vide.")
    try:
        result = ExplainResult.model_validate(json.loads(content))
    except (ValueError, ValidationError):
        raise LLMError("Le service d'IA a renvoyé une réponse mal formée. Réessayez.") from None
    if not result.en_clair.strip():
        raise LLMError("Le service d'IA a renvoyé une réponse vide.")
    return result
