from flask import Blueprint, current_app, request

from ..http import error_response, json_response
from ..services.observability import get_metrics

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    secret = current_app.config.get("METRICS_SECRET", "")
    if secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {secret}":
            return error_response(
                "Unauthorized",
                status=401,
                code="unauthorized",
            )

    snapshot = get_metrics().snapshot()
    snapshot["status"] = "ok"
    return json_response(snapshot)
