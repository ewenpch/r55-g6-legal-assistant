from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration du backend, surchargeable via un fichier .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_num_ctx: int = 4096


@lru_cache
def get_settings() -> Settings:
    return Settings()
