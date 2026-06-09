"""Tests for devpilot.ai.factory — provider selection and fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from devpilot.ai.factory import get_provider


class TestProviderSelection:
    """Tests for provider selection based on env var."""

    @patch.dict(
        "os.environ", {"DEVPILOT_AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"}, clear=True
    )
    def test_returns_openai_when_requested_and_available(self):
        """Returns OpenAIProvider when DEVPILOT_AI_PROVIDER=openai and key is set."""
        provider = get_provider()
        assert provider.__class__.__name__ == "OpenAIProvider"

    @patch.dict(
        "os.environ",
        {"DEVPILOT_AI_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-test"},
        clear=True,
    )
    @patch("devpilot.ai.factory._try_import_anthropic")
    def test_returns_anthropic_when_requested_and_available(self, mock_import):
        """Returns AnthropicProvider when DEVPILOT_AI_PROVIDER=anthropic and key is set."""
        mock_cls = MagicMock()
        mock_cls.return_value.is_available.return_value = True
        mock_cls.return_value.__class__.__name__ = "AnthropicProvider"
        mock_import.return_value = mock_cls
        provider = get_provider()
        assert provider.__class__.__name__ == "AnthropicProvider"

    @patch.dict(
        "os.environ", {"DEVPILOT_AI_PROVIDER": "gemini", "GEMINI_API_KEY": "sk-test"}, clear=True
    )
    @patch("devpilot.ai.factory._try_import_gemini")
    def test_returns_gemini_when_requested_and_available(self, mock_import):
        """Returns GeminiProvider when DEVPILOT_AI_PROVIDER=gemini and key is set."""
        mock_cls = MagicMock()
        mock_cls.return_value.is_available.return_value = True
        mock_cls.return_value.__class__.__name__ = "GeminiProvider"
        mock_import.return_value = mock_cls
        provider = get_provider()
        assert provider.__class__.__name__ == "GeminiProvider"

    @patch.dict("os.environ", {"DEVPILOT_AI_PROVIDER": "ollama"}, clear=True)
    @patch("devpilot.ai.providers.ollama.requests.get")
    def test_returns_ollama_when_available(self, mock_get):
        """Returns OllamaProvider when DEVPILOT_AI_PROVIDER=ollama and reachable."""
        mock_get.return_value.status_code = 200
        provider = get_provider()
        assert provider.__class__.__name__ == "OllamaProvider"


class TestFallbackBehavior:
    """Tests for auto-detection fallback when DEVPILOT_AI_PROVIDER is unset."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True)
    def test_falls_back_to_first_available_provider(self):
        """When DEVPILOT_AI_PROVIDER is unset, returns first available provider."""
        provider = get_provider()
        assert provider.__class__.__name__ == "OpenAIProvider"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_system_exit_when_no_provider_is_available(self):
        """Raises SystemExit when no provider has a configured key."""
        with pytest.raises(SystemExit):
            get_provider()


class TestErrorHandling:
    """Tests for error cases."""

    @patch.dict("os.environ", {"DEVPILOT_AI_PROVIDER": "unknown"}, clear=True)
    def test_raises_system_exit_for_unknown_provider(self):
        """Raises SystemExit when DEVPILOT_AI_PROVIDER is set to an unknown value."""
        with pytest.raises(SystemExit):
            get_provider()

    @patch.dict("os.environ", {"DEVPILOT_AI_PROVIDER": "openai"}, clear=True)
    def test_raises_system_exit_when_requested_provider_not_configured(self):
        """Raises SystemExit when requested provider has no API key."""
        with pytest.raises(SystemExit):
            get_provider()
