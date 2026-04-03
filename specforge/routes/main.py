from flask import Blueprint, current_app, jsonify, render_template, request

from ..services.prd import generate_prd

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    client_input = data.get("requirements", "")
    use_ai = data.get("ai_enhance", False)
    ai_provider = data.get("ai_provider", "minimax")

    if not client_input or len(client_input.strip()) < 10:
        return jsonify(
            {
                "success": False,
                "error": "Please enter at least 10 characters describing your requirements",
            }
        ), 400

    result = generate_prd(client_input, use_ai, ai_provider)
    return jsonify(result)


@main_bp.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "version": "2.0.0",
            "features": [
                "Domain detection",
                "Negative scope detection",
                "RMS calculation",
                "Clarification questions",
                "Conflict detection",
                "PRD generation",
                "MiniMax OAuth authentication",
                "MiniMax API integration",
            ],
            "ai_providers": {
                "minimax": {
                    "oauth_configured": bool(current_app.config["MINIMAX_CLIENT_ID"]),
                    "api_key_configured": bool(current_app.config["MINIMAX_API_KEY"]),
                }
            },
        }
    )
