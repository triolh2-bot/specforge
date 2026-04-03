from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session

from ..services.minimax import call_minimax_api

api_bp = Blueprint("api", __name__)


def minimax_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not session.get("minimax_authenticated") and not current_app.config["MINIMAX_API_KEY"]:
            return jsonify({"success": False, "error": "MiniMax authentication required"}), 401
        return func(*args, **kwargs)

    return decorated_function


@api_bp.route("/api/minimax/chat", methods=["POST"])
def minimax_chat():
    if not current_app.config["MINIMAX_API_KEY"] and not session.get("access_token"):
        return jsonify(
            {
                "success": False,
                "error": "Not authenticated. Use MiniMax OAuth or set MINIMAX_API_KEY",
            }
        ), 401

    data = request.json or {}
    message = data.get("message", "")
    model = data.get("model", "abab6.5s-chat")

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    payload = {"model": model, "messages": [{"role": "user", "content": message}]}
    response = call_minimax_api(
        "chat/completions",
        method="POST",
        data=payload,
        use_api_key=bool(current_app.config["MINIMAX_API_KEY"]),
    )

    if response:
        return jsonify({"success": True, "response": response})
    return jsonify({"success": False, "error": "Failed to get response from MiniMax"}), 500


@api_bp.route("/api/minimax/enhance", methods=["POST"])
def enhance_with_minimax():
    if not current_app.config["MINIMAX_API_KEY"] and not session.get("access_token"):
        return jsonify(
            {
                "success": False,
                "error": "MiniMax not configured. Set MINIMAX_API_KEY or authenticate via OAuth",
            }
        ), 401

    data = request.json or {}
    requirements = data.get("requirements", "")

    if not requirements:
        return jsonify({"success": False, "error": "Requirements are required"}), 400

    prompt = f"""Analyze these requirements and provide enhancement suggestions:

Requirements: {requirements}

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
        return jsonify(
            {
                "success": True,
                "enhancement": response["choices"][0]["message"]["content"],
                "model": response.get("model", "minimax"),
            }
        )
    return jsonify({"success": False, "error": "Failed to get enhancement from MiniMax"}), 500
