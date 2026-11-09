"""Seul point d'appel au LLM (Groq, API compatible OpenAI), côté serveur uniquement."""

from pathlib import Path

import httpx

from app.config import BACKEND_DIR, Settings

PROMPT_PATH = BACKEND_DIR / "prompts" / "explain-clause.md"
LLM_TIMEOUT = 30.0
TEMPERATURE = 0.2


class LLMError(Exception):
    """Erreur d'appel au LLM, avec un message lisible par l'utilisateur."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_system_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


async def explain_clause(client: httpx.AsyncClient, settings: Settings, text: str) -> str:
    """Envoie la clause au modèle et renvoie son explication en texte brut.

    Les messages d'erreur ne contiennent jamais la clé ni le texte de l'utilisateur.
    """
    if not settings.llm_api_key:
        raise LLMError("La clé d'API du LLM n'est pas configurée sur le serveur.", 503)

    payload = {
        "model": settings.llm_model,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": f"<clause>\n{text}\n</clause>"},
        ],
    }
    try:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=LLM_TIMEOUT,
        )
    except httpx.TimeoutException:
        raise LLMError("Le service d'IA a mis trop de temps à répondre. Réessayez.", 504) from None
    except httpx.HTTPError:
        raise LLMError("Impossible de joindre le service d'IA. Vérifiez la connexion.") from None

    if response.status_code in (401, 403):
        raise LLMError("La clé d'API du LLM est refusée par le service d'IA.", 502)
    if response.status_code == 429:
        raise LLMError("Trop de requêtes vers le service d'IA. Réessayez dans un instant.", 429)
    if response.status_code >= 400:
        raise LLMError(f"Le service d'IA a renvoyé une erreur ({response.status_code}).")

    try:
        answer = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMError("Réponse inattendue du service d'IA.") from None
    if not isinstance(answer, str) or not answer.strip():
        raise LLMError("Le service d'IA a renvoyé une réponse vide.")
    return answer.strip()
