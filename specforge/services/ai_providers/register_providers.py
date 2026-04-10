"""Helper to register all built-in providers into the registry."""

from __future__ import annotations

from .minimax_provider import MiniMaxProvider
from .registry import registry


def register_builtin_providers() -> None:
    """Register the MiniMax provider (and future providers) into *registry*."""
    minimax = MiniMaxProvider()
    registry.register(minimax, fallback=False)
