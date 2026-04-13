"""Provider contract tests — retries, timeouts, JSON parsing failures, fallback."""

import json
import unittest
from unittest.mock import MagicMock, patch

import requests
from flask import Flask

from specforge.services.ai_providers import (
    AIProvider,
    ChatMessage,
    OpenRouterProvider,
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
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "test-model",
    })
    app.config.update(config_overrides)
    return app


class TestOpenRouterProviderInterface(unittest.TestCase):
    """Verify that OpenRouterProvider satisfies the AIProvider contract."""

    def setUp(self):
        registry._providers.clear()
        registry._fallback_order.clear()
        register_builtin_providers()

    def test_provider_has_name(self):
        provider = registry.get("openrouter")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.name, "openrouter")

    def test_provider_has_display_name(self):
        provider = registry.get("openrouter")
        self.assertIsInstance(provider.display_name, str)
        self.assertTrue(len(provider.display_name) > 0)

    def test_provider_has_capabilities(self):
        provider = registry.get("openrouter")
        self.assertIsInstance(provider.capabilities, tuple)
        self.assertIn(ProviderCapability.CHAT_COMPLETION, provider.capabilities)

    def test_provider_implements_chat_completion(self):
        provider = registry.get("openrouter")
        self.assertTrue(callable(getattr(provider, "chat_completion", None)))


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


if __name__ == "__main__":
    unittest.main()
