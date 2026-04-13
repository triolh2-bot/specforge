"""Helper to register all built-in providers into the registry."""

from __future__ import annotations

from .openrouter_provider import OpenRouterProvider
from .registry import registry


def register_builtin_providers() -> None:
    """Register the built-in providers into *registry*."""
    openrouter = OpenRouterProvider()
    registry.register(openrouter, fallback=False)
