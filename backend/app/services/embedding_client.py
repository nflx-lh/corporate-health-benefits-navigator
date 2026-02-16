"""Provider-agnostic embedding client with OpenAI implementation.

Exposes a single ``embed()`` convenience function that never raises.
Returns ``None`` on any failure (timeout, missing key, disabled, etc.).
"""

import abc
import logging
import os
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(abc.ABC):
    """Abstract base for embedding providers."""

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> Optional[list[list[float]]]:
        """Return embeddings for *texts*, or None on failure."""


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider with lazy client init."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            settings = get_settings()
            timeout_s = settings.EMBEDDING_TIMEOUT_MS / 1000.0
            self._client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                timeout=timeout_s,
            )
        return self._client

    def embed(self, texts: list[str]) -> Optional[list[list[float]]]:
        settings = get_settings()
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as exc:
            logger.warning("OpenAI embedding call failed: %s", exc)
            return None


def get_embedding_provider() -> Optional[BaseEmbeddingProvider]:
    """Factory: select provider via EMBEDDING_PROVIDER setting.

    Returns None if provider is 'none' or unknown.
    """
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    return None


def _is_embedding_available() -> bool:
    """Check if embedding path should be used (key present + provider valid)."""
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER.lower() == "none":
        return False
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False
    return True


def embed(texts: list[str]) -> Optional[list[list[float]]]:
    """Top-level convenience function. Never raises, returns None on any failure."""
    if not _is_embedding_available():
        return None
    provider = get_embedding_provider()
    if provider is None:
        return None
    return provider.embed(texts)
