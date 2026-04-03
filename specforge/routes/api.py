from functools import wraps

from flask import Blueprint, current_app, session

from ..http import error_response, json_response
from ..services.minimax import call_minimax_api
from ..validation import validate_minimax_chat_request, validate_minimax_enhance_request

api_bp = Blueprint("api", __name__)


def minimax_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not session.get("minimax_authenticated") and not current_app.config["MINIMAX_API_KEY"]:
            return error_response("MiniMax authentication required", status=401, code="authentication_required")
        return func(*args, **kwargs)

    return decorated_function


@api_bp.route("/api/minimax/chat", methods=["POST"])
def minimax_chat():
    if not current_app.config["MINIMAX_API_KEY"] and not session.get("access_token"):
        return error_response(
            "Not authenticated. Use MiniMax OAuth or set MINIMAX_API_KEY",
            status=401,
            code="unauthorized",
        )
    data = validate_minimax_chat_request()

    payload = {"model": data["model"], "messages": [{"role": "user", "content": data["message"]}]}
    response = call_minimax_api(
        "chat/completions",
        method="POST",
        data=payload,
        use_api_key=bool(current_app.config["MINIMAX_API_KEY"]),
    )

    if response:
        return json_response({"success": True, "response": response})
    return error_response("Failed to get response from MiniMax", status=500, code="provider_request_failed")


@api_bp.route("/api/minimax/enhance", methods=["POST"])
def enhance_with_minimax():
    if not current_app.config["MINIMAX_API_KEY"] and not session.get("access_token"):
        return error_response(
            "MiniMax not configured. Set MINIMAX_API_KEY or authenticate via OAuth",
            status=401,
            code="unauthorized",
        )
    data = validate_minimax_enhance_request()

    prompt = f"""Analyze these requirements and provide enhancement suggestions:

Requirements: {data["requirements"]}

Provide:
1. Missing technical components
2. Security considerations
3. Scalability recommendations
4. User experience improvements
5. Potential risks

Be concise and actionable."""

    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {"role": "system", "content": "You are a senior software architect helping to refine project requirements."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    response = call_minimax_api(
        "chat/completions",
        method="POST",
        data=payload,
        use_api_key=bool(current_app.config["MINIMAX_API_KEY"]),
    )

    if response and "choices" in response:
        return json_response(
            {
                "success": True,
                "enhancement": response["choices"][0]["message"]["content"],
                "model": response.get("model", "minimax"),
            }
        )
    return error_response("Failed to get enhancement from MiniMax", status=500, code="provider_request_failed")
