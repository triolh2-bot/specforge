"""API routes — provider proxy endpoints."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, session

from ..http import error_response, json_response
from ..services.ai_providers import ChatMessage, registry
from ..services.auth_session import get_minimax_auth_status
from ..services.abuse import rate_limit
from ..validation import validate_minimax_chat_request, validate_minimax_enhance_request

api_bp = Blueprint("api", __name__)


def _any_provider_available() -> bool:
    return registry.select() is not None


def minimax_required(func):
    """Decorator that ensures at least one AI provider is available."""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        auth_state = get_minimax_auth_status()
        if not auth_state["authenticated"] and not current_app.config["MINIMAX_API_KEY"]:
            if not _any_provider_available():
                return error_response("AI provider authentication required", status=401, code="authentication_required")
        return func(*args, **kwargs)

    return decorated_function


@api_bp.route("/api/minimax/chat", methods=["POST"])
@minimax_required
@rate_limit("minimax_chat")
def minimax_chat():
    data = validate_minimax_chat_request()

    provider = registry.select()
    if provider is None:
        return error_response("No AI provider available", status=503, code="no_provider_available")

    messages = [
        ChatMessage(role="user", content=data["message"]),
    ]

    model = data.get("model") or current_app.config.get("MINIMAX_MODEL")

    result = provider.chat_completion(messages, model=model)

    if result.success:
        return json_response({
            "success": True,
            "response": result.data,
            "provider": provider.name,
            "model": result.model,
        })
    return error_response(
        f"Provider request failed: {result.error}",
        status=500,
        code="provider_request_failed",
    )


@api_bp.route("/api/minimax/enhance", methods=["POST"])
@minimax_required
@rate_limit("minimax_enhance")
def enhance_with_provider():
    data = validate_minimax_enhance_request()

    provider = registry.select()
    if provider is None:
        return error_response("No AI provider available", status=503, code="no_provider_available")

    prompt = (
        f"Analyze these requirements and provide enhancement suggestions:\n\n"
        f"Requirements: {data['requirements']}\n\n"
        f"Provide:\n"
        f"1. Missing technical components\n"
        f"2. Security considerations\n"
        f"3. Scalability recommendations\n"
        f"4. User experience improvements\n"
        f"5. Potential risks\n\n"
        f"Be concise and actionable."
    )

    messages = [
        ChatMessage(
            role="system",
            content="You are a senior software architect helping to refine project requirements.",
        ),
        ChatMessage(role="user", content=prompt),
    ]

    model = current_app.config.get("MINIMAX_MODEL")

    result = provider.chat_completion(messages, model=model)

    if result.success:
        raw_content = result.data.get("raw_content", "")
        return json_response({
            "success": True,
            "enhancement": raw_content or str(result.data),
            "provider": provider.name,
            "model": result.model,
        })
    return error_response(
        f"Provider request failed: {result.error}",
        status=500,
        code="provider_request_failed",
    )


@api_bp.route("/api/providers", methods=["GET"])
def list_providers():
    """Return all registered AI providers with their status and capabilities."""
    providers = []
    for provider in registry.list_providers():
        providers.append({
            "name": provider.name,
            "display_name": provider.display_name,
            "capabilities": [c.value for c in provider.capabilities],
            "configured": provider.is_configured(),
            "status": provider.health_check().value,
            "models": provider.get_available_models(),
        })

    available = registry.get_available_providers()
    preferred = registry.select()

    return json_response({
        "providers": providers,
        "available": [p.name for p in available],
        "preferred": preferred.name if preferred else None,
    })
