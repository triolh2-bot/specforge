"""OpenRouter provider adapter — implements the ``AIProvider`` interface."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests
from flask import current_app, request

from .base import AIProvider, ChatMessage, ProviderCapability, ProviderResponse, ProviderStatus

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "openai/gpt-4o-mini"
_CHAT_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(AIProvider):
    """Adapter for the OpenRouter chat-completion API."""

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def display_name(self) -> str:
        return "OpenRouter (OpenAI-compatible)"

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return (
            ProviderCapability.CHAT_COMPLETION,
            ProviderCapability.REQUIREMENT_ENHANCE,
        )

    def is_configured(self) -> bool:
        return bool(current_app.config.get("OPENROUTER_API_KEY"))

    def get_available_models(self) -> tuple[str, ...]:
        return (
            current_app.config.get("OPENROUTER_MODEL", _DEFAULT_MODEL),
            "anthropic/claude-3.5-sonnet",
            "google/gemini-1.5-flash",
            "openai/gpt-4o",
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
        model = model or current_app.config.get("OPENROUTER_MODEL", _DEFAULT_MODEL)

        if not current_app.config.get("OPENROUTER_API_KEY"):
            return ProviderResponse(success=False, error="OpenRouter API key not configured")

        site_url = current_app.config.get("OPENROUTER_SITE_URL")
        if not site_url:
            try:
                site_url = request.host_url
            except RuntimeError:
                site_url = "https://specforge.dev"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['OPENROUTER_API_KEY']}",
            "HTTP-Referer": site_url,
            "X-Title": "SpecForge",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Merge any extra kwargs the caller passed through
        payload.update(kwargs)

        try:
            resp = requests.post(_CHAT_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
        except requests.exceptions.Timeout:
            logger.error("OpenRouter API call timed out")
            return ProviderResponse(success=False, error="OpenRouter API call timed out", model=model)
        except requests.exceptions.RequestException as exc:
            logger.error("OpenRouter API call failed: %s", exc)
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 429:
                return ProviderResponse(
                    success=False,
                    error="OpenRouter rate limit exceeded. Too many requests. Please wait a moment and try again.",
                    model=model,
                )
            return ProviderResponse(success=False, error=str(exc), model=model)
        except Exception as exc:
            logger.error("Unexpected error calling OpenRouter API: %s", exc)
            return ProviderResponse(success=False, error=str(exc), model=model)

        # ---- parse OpenAI-specific response format ----
        if "error" in result:
            error_obj = result.get("error", {})
            status_msg = error_obj.get("message", "Unknown OpenRouter Error")
            logger.warning("OpenRouter API error: %s", status_msg)
            return ProviderResponse(success=False, error=status_msg, model=model)

        if "choices" not in result or not result["choices"]:
            logger.warning("Unexpected OpenRouter response format: no choices")
            return ProviderResponse(success=False, error="No choices in response", model=model)

        choice = result["choices"][0]
        content = choice.get("message", {}).get("content", "")
        usage = result.get("usage")

        # Try to extract JSON from markdown-wrapped responses
        data = self._extract_json(content) or {}
        data["raw_content"] = content

        return ProviderResponse(
            success=True,
            data=data,
            model=result.get("model", model),
            usage=usage,
        )

    def health_check(self) -> ProviderStatus:
        if not self.is_configured():
            return ProviderStatus.UNHEALTHY
        return ProviderStatus.HEALTHY

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Optional[dict[str, Any]]:
        """Extract the first top-level JSON object from *text*."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON block delimited by format tags
        try:
            if "```json" in text:
                block = text.split("```json")[1].split("```")[0]
                return json.loads(block.strip())
        except Exception:
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
