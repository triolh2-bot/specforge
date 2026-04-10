"""Provider contract tests — retries, timeouts, JSON parsing failures, fallback."""

import json
import unittest
from unittest.mock import MagicMock, patch

import requests
from flask import Flask

from specforge.services.ai_providers import (
    AIProvider,
    ChatMessage,
    MiniMaxProvider,
    ProviderCapability,
    ProviderResponse,
    ProviderStatus,
    registry,
    register_builtin_providers,
)


def _make_app(**config_overrides):
    """Create a minimal Flask app with the given config."""
    app = Flask(__name__)
    app.config.update({
        "MINIMAX_API_KEY": "",
        "MINIMAX_CLIENT_ID": "",
        "MINIMAX_GROUP_ID": "",
        "MINIMAX_MODEL": "test-model",
    })
    app.config.update(config_overrides)
    return app


class TestMiniMaxProviderInterface(unittest.TestCase):
    """Verify that MiniMaxProvider satisfies the AIProvider contract."""

    def setUp(self):
        registry._providers.clear()
        registry._fallback_order.clear()
        register_builtin_providers()

    def test_provider_has_name(self):
        provider = registry.get("minimax")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.name, "minimax")

    def test_provider_has_display_name(self):
        provider = registry.get("minimax")
        self.assertIsInstance(provider.display_name, str)
        self.assertTrue(len(provider.display_name) > 0)

    def test_provider_has_capabilities(self):
        provider = registry.get("minimax")
        self.assertIsInstance(provider.capabilities, tuple)
        self.assertIn(ProviderCapability.CHAT_COMPLETION, provider.capabilities)

    def test_provider_implements_chat_completion(self):
        provider = registry.get("minimax")
        self.assertTrue(callable(getattr(provider, "chat_completion", None)))


class TestMiniMaxProviderTimeout(unittest.TestCase):
    """Timeout handling in the MiniMax provider."""

    def test_timeout_returns_failure_response(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            with patch("specforge.services.ai_providers.minimax_provider.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="hello")],
                )

                self.assertFalse(result.success)
                self.assertIn("timed out", result.error)
                self.assertEqual(result.model, "test-model")


class TestMiniMaxProviderJSONParsing(unittest.TestCase):
    """JSON extraction from provider responses."""

    def test_parses_clean_json(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            expected = {"prd_summary": "Test summary", "clarification_questions": ["Q1"]}
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": json.dumps(expected)}}],
                "model": "test-model",
            }

            with patch("specforge.services.ai_providers.minimax_provider.requests.post", return_value=mock_response):
                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertTrue(result.success)
                self.assertEqual(result.data["prd_summary"], "Test summary")
                self.assertEqual(result.data["clarification_questions"], ["Q1"])

    def test_parses_json_in_markdown_block(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            expected = {"prd_summary": "Wrapped summary"}
            content = "```json\n" + json.dumps(expected) + "\n```"
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": content}}],
                "model": "test-model",
            }

            with patch("specforge.services.ai_providers.minimax_provider.requests.post", return_value=mock_response):
                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertTrue(result.success)
                self.assertEqual(result.data["prd_summary"], "Wrapped summary")

    def test_handles_invalid_json_gracefully(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "This is not JSON at all!"}}],
                "model": "test-model",
            }

            with patch("specforge.services.ai_providers.minimax_provider.requests.post", return_value=mock_response):
                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertTrue(result.success)
                self.assertIn("raw_content", result.data)
                self.assertEqual(result.data["raw_content"], "This is not JSON at all!")


class TestMiniMaxProviderErrorResponses(unittest.TestCase):
    """Provider error handling — API errors, malformed responses."""

    def test_api_error_returns_failure(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "base_resp": {"status_msg": "Rate limited"}
            }

            with patch("specforge.services.ai_providers.minimax_provider.requests.post", return_value=mock_response):
                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertFalse(result.success)
                self.assertEqual(result.error, "Rate limited")

    def test_no_choices_returns_failure(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"unexpected_key": "value"}

            with patch("specforge.services.ai_providers.minimax_provider.requests.post", return_value=mock_response):
                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertFalse(result.success)
                self.assertIn("No choices", result.error)

    def test_request_exception_returns_failure(self):
        app = _make_app(MINIMAX_API_KEY="test-key", MINIMAX_GROUP_ID="test-group")
        with app.app_context():
            with patch("specforge.services.ai_providers.minimax_provider.requests.post") as mock_post:
                mock_post.side_effect = requests.exceptions.ConnectionError("DNS failure")

                provider = MiniMaxProvider()
                result = provider.chat_completion(
                    [ChatMessage(role="user", content="test")],
                )

                self.assertFalse(result.success)
                self.assertIn("DNS failure", result.error)


class TestProviderRegistryFallback(unittest.TestCase):
    """Registry fallback behavior when preferred provider is unavailable."""

    def setUp(self):
        registry._providers.clear()
        registry._fallback_order.clear()

    def test_returns_none_when_no_providers(self):
        self.assertIsNone(registry.select())

    def test_returns_preferred_when_available(self):
        mock_provider = MagicMock(spec=AIProvider)
        mock_provider.name = "test"
        mock_provider.is_configured.return_value = True
        mock_provider.health_check.return_value = ProviderStatus.HEALTHY
        registry.register(mock_provider)

        result = registry.select("test")
        self.assertEqual(result, mock_provider)

    def test_fallback_when_preferred_unavailable(self):
        preferred = MagicMock(spec=AIProvider)
        preferred.name = "preferred"
        preferred.is_configured.return_value = False

        fallback = MagicMock(spec=AIProvider)
        fallback.name = "fallback"
        fallback.is_configured.return_value = True
        fallback.health_check.return_value = ProviderStatus.HEALTHY

        registry.register(preferred)
        registry.register(fallback, fallback=True)

        result = registry.select("preferred")
        self.assertEqual(result, fallback)

    def test_healthy_provider_selected(self):
        healthy = MagicMock(spec=AIProvider)
        healthy.name = "healthy"
        healthy.is_configured.return_value = True
        healthy.health_check.return_value = ProviderStatus.HEALTHY

        unhealthy = MagicMock(spec=AIProvider)
        unhealthy.name = "unhealthy"
        unhealthy.is_configured.return_value = True
        unhealthy.health_check.return_value = ProviderStatus.UNHEALTHY

        registry.register(unhealthy)
        registry.register(healthy)

        result = registry.select()
        self.assertEqual(result, healthy)


class TestProviderNotConfigured(unittest.TestCase):
    """Provider reports not configured when credentials are missing."""

    def test_not_configured_without_api_key_or_client_id(self):
        app = _make_app(MINIMAX_API_KEY="", MINIMAX_CLIENT_ID="")
        with app.app_context():
            provider = MiniMaxProvider()
            self.assertFalse(provider.is_configured())

    def test_configured_with_api_key(self):
        app = _make_app(MINIMAX_API_KEY="some-key", MINIMAX_CLIENT_ID="")
        with app.app_context():
            provider = MiniMaxProvider()
            self.assertTrue(provider.is_configured())

    def test_configured_with_client_id(self):
        app = _make_app(MINIMAX_API_KEY="", MINIMAX_CLIENT_ID="some-client")
        with app.app_context():
            provider = MiniMaxProvider()
            self.assertTrue(provider.is_configured())


if __name__ == "__main__":
    unittest.main()
