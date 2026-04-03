from flask import Blueprint, current_app, g, render_template

from ..contracts import HealthResponse
from ..http import json_response
from ..services.analysis_store import persist_analysis
from ..services.prd import generate_prd
from ..validation import validate_analyze_request

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/analyze", methods=["POST"])
def analyze():
    data = validate_analyze_request()
    result = generate_prd(data["requirements"], data["ai_enhance"], data["ai_provider"])
    result = persist_analysis(
        data["requirements"],
        data["ai_enhance"],
        data["ai_provider"],
        result,
        request_id=getattr(g, "request_id", None),
    )
    return json_response(result)


@main_bp.route("/health", methods=["GET"])
def health():
    payload: HealthResponse = {
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
        }
    }
    return json_response(payload)
