"""Helper to register all built-in providers into the registry."""

from __future__ import annotations

from .minimax_provider import MiniMaxProvider
from .openrouter_provider import OpenRouterProvider
from .registry import registry


def register_builtin_providers() -> None:
    """Register the built-in providers into *registry*."""
    minimax = MiniMaxProvider()
    openrouter = OpenRouterProvider()
    registry.register(minimax, fallback=False)
    registry.register(openrouter, fallback=False)
