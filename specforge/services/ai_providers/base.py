"""Provider abstraction layer base types and abstract interface."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums / constants
# ---------------------------------------------------------------------------

class ProviderCapability(str, Enum):
    """Feature flags that a provider may support."""

    CHAT_COMPLETION = "chat_completion"
    REQUIREMENT_ENHANCE = "requirement_enhance"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    TOOL_USE = "tool_use"


class ProviderStatus(str, Enum):
    """Runtime health of a registered provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderInfo:
    """Metadata returned when listing registered providers."""

    name: str
    display_name: str
    capabilities: tuple[ProviderCapability, ...]
    status: ProviderStatus = ProviderStatus.HEALTHY
    models: tuple[str, ...] = ()
    config_keys: tuple[str, ...] = ()


@dataclass
class ProviderResponse:
    """Normalised response from any AI provider."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[dict[str, int]] = None  # {prompt_tokens, completion_tokens, total_tokens}


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str  # "system", "user", "assistant"
    content: str


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class AIProvider(abc.ABC):
    """Base class every provider adapter must implement."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique provider identifier, e.g. ``"openrouter"``."""

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. ``"OpenRouter"``."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        """Feature flags describing what this provider supports."""

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Return ``True`` when the provider has valid credentials / config."""

    @abc.abstractmethod
    def chat_completion(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Send a chat-completion request and return a normalised response."""

    def get_available_models(self) -> tuple[str, ...]:
        """Return the list of model identifiers this provider supports."""
        return ()

    def health_check(self) -> ProviderStatus:
        """Optional lightweight probe; defaults to HEALTHY if configured."""
        return ProviderStatus.HEALTHY if self.is_configured() else ProviderStatus.UNHEALTHY
