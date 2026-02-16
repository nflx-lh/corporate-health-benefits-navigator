"""Centralised application settings – reads from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration sourced from env vars with sensible defaults."""

    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "chbn-api")

    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai | none
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    LLM_TIMEOUT_MS: int = int(os.getenv("LLM_TIMEOUT_MS", "5000"))
    MAX_EXPLAINER_RETRIES: int = int(os.getenv("MAX_EXPLAINER_RETRIES", "1"))

    # Embedding
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai | none
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_TIMEOUT_MS: int = int(os.getenv("EMBEDDING_TIMEOUT_MS", "10000"))

    # Rate limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "60/minute")

    # CORS
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "").split(",")
        if o.strip()
    ]

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def cors_origins(self) -> list[str]:
        """Return effective CORS origins – wildcard in dev, explicit otherwise."""
        if self.is_dev and not self.CORS_ORIGINS:
            return ["*"]
        return self.CORS_ORIGINS

    def validate_secrets(self) -> None:
        """Raise on startup if secrets are insecure in non-dev environments."""
        if not self.is_dev and self.JWT_SECRET == "change_me":
            raise ValueError(
                "JWT_SECRET must not be 'change_me' in non-development environments. "
                "Set a strong secret via the JWT_SECRET environment variable."
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
