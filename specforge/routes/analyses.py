from flask import Blueprint, request

from ..http import error_response, json_response
from ..services.analysis_store import fetch_analysis, fetch_analysis_history

analyses_bp = Blueprint("analyses", __name__)


def _parse_positive_int(value, default):
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


@analyses_bp.route("/api/analyses", methods=["GET"])
def list_analyses():
    limit = _parse_positive_int(request.args.get("limit"), 20)
    offset = _parse_positive_int(request.args.get("offset"), 0)

    if limit is None or offset is None:
        return error_response(
            "Query parameters 'limit' and 'offset' must be non-negative integers",
            status=400,
            code="invalid_query_parameter",
        )

    limit = min(limit, 100)
    payload = fetch_analysis_history(limit=limit, offset=offset)
    return json_response(payload)


@analyses_bp.route("/api/analyses/<analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    payload = fetch_analysis(analysis_id)
    if not payload:
        return error_response("Analysis not found", status=404, code="analysis_not_found")
    return json_response(payload)
