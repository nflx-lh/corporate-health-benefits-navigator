"""Tests for the provider-agnostic embedding client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding_client import (
    OpenAIEmbeddingProvider,
    _is_embedding_available,
    embed,
    get_embedding_provider,
)


# ------------------------------------------------------------------
# Factory tests
# ------------------------------------------------------------------

class TestGetEmbeddingProvider:

    @patch("app.services.embedding_client.get_settings")
    def test_openai_provider(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        provider = get_embedding_provider()
        assert isinstance(provider, OpenAIEmbeddingProvider)

    @patch("app.services.embedding_client.get_settings")
    def test_none_provider_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="none")
        assert get_embedding_provider() is None

    @patch("app.services.embedding_client.get_settings")
    def test_unknown_provider_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="cohere")
        assert get_embedding_provider() is None


# ------------------------------------------------------------------
# Availability check
# ------------------------------------------------------------------

class TestIsEmbeddingAvailable:

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    def test_all_conditions_met(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        assert _is_embedding_available() is True

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.services.embedding_client.get_settings")
    def test_no_api_key_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        assert _is_embedding_available() is False

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    def test_provider_none_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="none")
        assert _is_embedding_available() is False


# ------------------------------------------------------------------
# embed() convenience function
# ------------------------------------------------------------------

class TestEmbed:

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.services.embedding_client.get_settings")
    def test_no_api_key_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        result = embed(["hello"])
        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    @patch("app.services.embedding_client.get_embedding_provider")
    def test_success_returns_embeddings(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        mock_provider = MagicMock()
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_provider_fn.return_value = mock_provider
        result = embed(["hello"])
        assert result == [[0.1, 0.2, 0.3]]

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    @patch("app.services.embedding_client.get_embedding_provider")
    def test_provider_failure_returns_none(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        mock_provider = MagicMock()
        mock_provider.embed.return_value = None
        mock_provider_fn.return_value = mock_provider
        result = embed(["hello"])
        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    @patch("app.services.embedding_client.get_embedding_provider")
    def test_provider_none_returns_none(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        mock_provider_fn.return_value = None
        result = embed(["hello"])
        assert result is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.services.embedding_client.get_settings")
    @patch("app.services.embedding_client.get_embedding_provider")
    def test_batch_embed(self, mock_provider_fn, mock_settings):
        mock_settings.return_value = MagicMock(EMBEDDING_PROVIDER="openai")
        mock_provider = MagicMock()
        mock_provider.embed.return_value = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_provider_fn.return_value = mock_provider
        result = embed(["a", "b", "c"])
        assert result is not None
        assert len(result) == 3


# ------------------------------------------------------------------
# OpenAIEmbeddingProvider exception handling
# ------------------------------------------------------------------

class TestOpenAIEmbeddingProvider:

    @patch("app.services.embedding_client.get_settings")
    def test_exception_returns_none(self, mock_settings):
        mock_settings.return_value = MagicMock(
            EMBEDDING_MODEL="text-embedding-3-small",
            EMBEDDING_TIMEOUT_MS=10000,
        )
        provider = OpenAIEmbeddingProvider()
        # Mock the internal client to raise
        provider._client = MagicMock()
        provider._client.embeddings.create.side_effect = Exception("timeout")
        result = provider.embed(["hello"])
        assert result is None
