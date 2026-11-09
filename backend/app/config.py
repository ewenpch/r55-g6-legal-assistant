import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Sur Vercel, seul /tmp est inscriptible (et il est éphémère : voir README, « Déploiement »).
DEFAULT_DB_PATH = (
    Path("/tmp/app.db") if os.environ.get("VERCEL") else BACKEND_DIR / "data" / "app.db"
)


class Settings(BaseSettings):
    """Configuration du backend, surchargeable via backend/.env (jamais commite)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"

    database_path: Path = DEFAULT_DB_PATH
    # Mettre COOKIE_SECURE=true derrière HTTPS.
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
