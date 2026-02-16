"""Provider-agnostic LLM client with OpenAI implementation.

Exposes a single ``chat_completion()`` convenience function that never raises.
Returns ``None`` on any failure (timeout, missing key, disabled, etc.).
"""

import abc
import logging
import os
import time
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(abc.ABC):
    """Abstract base for LLM providers."""

    @abc.abstractmethod
    def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """Return completion text, or None on failure."""


class OpenAIProvider(BaseLLMProvider):
    """OpenAI chat completion provider with lazy client init."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            settings = get_settings()
            timeout_s = settings.LLM_TIMEOUT_MS / 1000.0
            self._client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                timeout=timeout_s,
            )
        return self._client

    def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> Optional[str]:
        settings = get_settings()
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("OpenAI call failed: %s", exc)
            return None


def get_llm_provider() -> Optional[BaseLLMProvider]:
    """Factory: select provider via LLM_PROVIDER setting.

    Returns None if provider is 'none' or unknown.
    """
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIProvider()
    return None


def _is_llm_available() -> bool:
    """Check if LLM path should be used (enabled + key present + provider valid)."""
    settings = get_settings()
    if not settings.LLM_ENABLED:
        return False
    if settings.LLM_PROVIDER.lower() == "none":
        return False
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False
    return True


def chat_completion(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Optional[str]:
    """Top-level convenience function. Never raises, returns None on any failure."""
    if not _is_llm_available():
        return None
    provider = get_llm_provider()
    if provider is None:
        return None
    return provider.chat_completion(system_prompt, user_message, temperature, max_tokens)
