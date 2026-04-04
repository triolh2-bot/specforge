from flask import Blueprint

from ..http import json_response
from ..services.observability import get_metrics

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    snapshot = get_metrics().snapshot()
    snapshot["status"] = "ok"
    return json_response(snapshot)
