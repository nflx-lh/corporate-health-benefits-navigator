"""Tests for the provider-agnostic LLM client (Phase 8)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_client import (
    OpenAIProvider,
    _is_llm_available,
    chat_completion,
    get_llm_provider,
)


# ------------------------------------------------------------------
# Factory tests
# ------------------------------------------------------------------

class TestGetLLMProvider:

    @patch("app.services.llm_client.get_settings")
    def test_openai_provider(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_PROVIDER="openai")
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.services.llm_client.get_settings")
    def test_none_provider_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_PROVIDER="none")
        assert get_llm_provider() is None

    @patch("app.services.llm_client.get_settings")
    def test_unknown_provider_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_PROVIDER="anthropic")
        assert get_llm_provider() is None


# ------------------------------------------------------------------
# Availability check
# ------------------------------------------------------------------

class TestIsLLMAvailable:

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    def test_all_conditions_met(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        assert _is_llm_available() is True

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    def test_disabled_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=False, LLM_PROVIDER="openai")
        assert _is_llm_available() is False

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.services.llm_client.get_settings")
    def test_no_api_key_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        assert _is_llm_available() is False

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    def test_provider_none_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="none")
        assert _is_llm_available() is False


# ------------------------------------------------------------------
# chat_completion convenience function
# ------------------------------------------------------------------

class TestChatCompletion:

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.services.llm_client.get_settings")
    def test_no_api_key_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        result = chat_completion("system", "user")
        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    @patch("app.services.llm_client.get_llm_provider")
    def test_success_returns_content(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        mock_provider = MagicMock()
        mock_provider.chat_completion.return_value = "Hello world"
        mock_provider_fn.return_value = mock_provider
        result = chat_completion("system", "user")
        assert result == "Hello world"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    @patch("app.services.llm_client.get_llm_provider")
    def test_timeout_returns_none(self, mock_provider_fn, mock_settings):
        """Simulate a timeout exception from the provider."""
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        mock_provider = MagicMock()
        mock_provider.chat_completion.return_value = None  # provider catches and returns None
        mock_provider_fn.return_value = mock_provider
        result = chat_completion("system", "user")
        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.llm_client.get_settings")
    @patch("app.services.llm_client.get_llm_provider")
    def test_provider_none_returns_none(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        mock_provider_fn.return_value = None
        result = chat_completion("system", "user")
        assert result is None


# ------------------------------------------------------------------
# OpenAIProvider exception handling
# ------------------------------------------------------------------

class TestOpenAIProvider:

    @patch("app.services.llm_client.get_settings")
    def test_exception_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(
            LLM_MODEL_NAME="gpt-4o-mini",
            LLM_TIMEOUT_MS=5000,
        )
        provider = OpenAIProvider()
        # Mock the internal client to raise
        provider._client = MagicMock()
        provider._client.chat.completions.create.side_effect = Exception("timeout")
        result = provider.chat_completion("system", "user")
        assert result is None
