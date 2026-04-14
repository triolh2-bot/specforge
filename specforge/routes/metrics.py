from flask import Blueprint, current_app, request

from ..http import error_response, json_response
from ..services.observability import get_metrics

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    secret = current_app.config.get("METRICS_SECRET")
    auth_header = request.headers.get("Authorization", "")
    
    if not secret or auth_header != f"Bearer {secret}":
        return error_response(
            "Unauthorized",
            status=401,
            code="unauthorized",
            details="METRICS_SECRET must be configured and provided via Bearer token"
        )

    snapshot = get_metrics().snapshot()
    snapshot["status"] = "ok"
    return json_response(snapshot)
