"""Provider registry — discovery, selection, and fallback for AI providers."""

from __future__ import annotations

import logging
from typing import Optional

from .base import AIProvider, ProviderStatus

logger = logging.getLogger(__name__)


class _ProviderRegistry:
    """Thread-safe singleton-style registry for AI providers."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._fallback_order: list[str] = []

    # -- registration -------------------------------------------------------

    def register(self, provider: AIProvider, *, fallback: bool = False) -> None:
        """Register a provider. If *fallback* is ``True``, it will be tried
        after all non-fallback providers during selection."""
        self._providers[provider.name] = provider
        if fallback:
            self._fallback_order.append(provider.name)

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)
        if name in self._fallback_order:
            self._fallback_order.remove(name)

    def reset(self) -> None:
        """Remove all registered providers.  Used during app init for test isolation."""
        self._providers.clear()
        self._fallback_order.clear()

    # -- lookup -------------------------------------------------------------

    def get(self, name: str) -> Optional[AIProvider]:
        return self._providers.get(name)

    def list_providers(self) -> list[AIProvider]:
        return list(self._providers.values())

    def get_available_providers(self) -> list[AIProvider]:
        """Return providers that are currently configured and healthy."""
        return [
            p for p in self._providers.values()
            if p.is_configured() and p.health_check() != ProviderStatus.UNHEALTHY
        ]

    # -- selection / fallback -----------------------------------------------

    def select(self, preferred: Optional[str] = None) -> Optional[AIProvider]:
        """Return the best available provider.

        Priority order:
        1. The explicitly requested provider (if configured & healthy)
        2. Any non-fallback provider that is configured & healthy
        3. First fallback provider that is configured & healthy
        4. ``None``
        """
        if preferred:
            provider = self._providers.get(preferred)
            if provider and provider.is_configured() and provider.health_check() != ProviderStatus.UNHEALTHY:
                return provider
            logger.warning("Preferred provider '%s' unavailable, falling back", preferred)

        # Try non-fallback providers first
        for provider in self._providers.values():
            if provider.name in self._fallback_order:
                continue
            if provider.is_configured() and provider.health_check() != ProviderStatus.UNHEALTHY:
                return provider

        # Try fallbacks
        for fb_name in self._fallback_order:
            provider = self._providers.get(fb_name)
            if provider and provider.is_configured() and provider.health_check() != ProviderStatus.UNHEALTHY:
                return provider

        logger.warning("No AI provider available")
        return None


# Module-level singleton
registry = _ProviderRegistry()
