"""MiniMax provider adapter — implements the ``AIProvider`` interface."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests
from flask import current_app

from .base import AIProvider, ChatMessage, ProviderCapability, ProviderResponse, ProviderStatus

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "MiniMax-M2.5"
_CHAT_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"


class MiniMaxProvider(AIProvider):
    """Adapter for the MiniMax chat-completion API."""

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def display_name(self) -> str:
        return "MiniMax AI"

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return (
            ProviderCapability.CHAT_COMPLETION,
            ProviderCapability.REQUIREMENT_ENHANCE,
        )

    def is_configured(self) -> bool:
        return bool(
            current_app.config.get("MINIMAX_API_KEY")
            or current_app.config.get("MINIMAX_CLIENT_ID")
        )

    def get_available_models(self) -> tuple[str, ...]:
        return (
            current_app.config.get("MINIMAX_MODEL", _DEFAULT_MODEL),
            "abab6.5s-chat",
            "abab6-chat",
        )

    # -- public API ---------------------------------------------------------

    def chat_completion(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> ProviderResponse:
        model = model or current_app.config.get("MINIMAX_MODEL", _DEFAULT_MODEL)
        group_id = current_app.config.get("MINIMAX_GROUP_ID", "")

        if not current_app.config.get("MINIMAX_API_KEY"):
            return ProviderResponse(success=False, error="MiniMax API key not configured")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['MINIMAX_API_KEY']}",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Merge any extra kwargs the caller passed through
        payload.update(kwargs)

        url = f"{_CHAT_API_URL}?GroupId={group_id}" if group_id else _CHAT_API_URL

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
        except requests.exceptions.Timeout:
            logger.error("MiniMax API call timed out")
            return ProviderResponse(success=False, error="MiniMax API call timed out", model=model)
        except requests.exceptions.RequestException as exc:
            logger.error("MiniMax API call failed: %s", exc)
            return ProviderResponse(success=False, error=str(exc), model=model)
        except Exception as exc:
            logger.error("Unexpected error calling MiniMax API: %s", exc)
            return ProviderResponse(success=False, error=str(exc), model=model)

        # ---- parse MiniMax-specific response format ----
        if "base_resp" in result:
            status_msg = result["base_resp"].get("status_msg", "Unknown error")
            logger.warning("MiniMax API error: %s", status_msg)
            return ProviderResponse(success=False, error=status_msg, model=model)

        if "choices" not in result or not result["choices"]:
            logger.warning("Unexpected MiniMax response format: no choices")
            return ProviderResponse(success=False, error="No choices in response", model=model)

        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage")

        # Try to extract JSON from markdown-wrapped responses
        data = self._extract_json(content)

        return ProviderResponse(
            success=True,
            data=data if data is not None else {"raw_content": content},
            model=result.get("model", model),
            usage=usage,
        )

    def health_check(self) -> ProviderStatus:
        if not self.is_configured():
            return ProviderStatus.UNHEALTHY
        # A lightweight probe — just check that the API key is non-empty.
        # A fuller check would ping the models list endpoint if available.
        return ProviderStatus.HEALTHY

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Optional[dict[str, Any]]:
        """Extract the first top-level JSON object from *text*."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON block delimited by braces
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse extracted JSON block: %s", exc)
        return None
