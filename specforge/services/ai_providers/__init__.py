"""AI provider abstraction package.

Usage::

    from specforge.services.ai_providers import (
        AIProvider,
        ChatMessage,
        ProviderCapability,
        ProviderInfo,
        ProviderResponse,
        ProviderStatus,
        registry,
        register_builtin_providers,
    )
"""

from .base import AIProvider, ChatMessage, ProviderCapability, ProviderInfo, ProviderResponse, ProviderStatus
from .minimax_provider import MiniMaxProvider
from .openrouter_provider import OpenRouterProvider
from .registry import registry
from .register_providers import register_builtin_providers

__all__ = [
    "AIProvider",
    "ChatMessage",
    "MiniMaxProvider",
    "OpenRouterProvider",
    "ProviderCapability",
    "ProviderInfo",
    "ProviderResponse",
    "ProviderStatus",
    "register_builtin_providers",
    "registry",
]
