from flask import Blueprint, request

from ..http import error_response, json_response
from ..services.abuse import rate_limit
from ..services.auth_session import ensure_workspace_context
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
@rate_limit("list_analyses")
def list_analyses():
    workspace = ensure_workspace_context()
    limit = _parse_positive_int(request.args.get("limit"), 20)
    offset = _parse_positive_int(request.args.get("offset"), 0)

    if limit is None or offset is None:
        return error_response(
            "Query parameters 'limit' and 'offset' must be non-negative integers",
            status=400,
            code="invalid_query_parameter",
        )

    limit = min(limit, 100)
    payload = fetch_analysis_history(workspace["workspace_id"], limit=limit, offset=offset)
    return json_response(payload)


@analyses_bp.route("/api/analyses/<analysis_id>", methods=["GET"])
@rate_limit("get_analysis")
def get_analysis(analysis_id):
    workspace = ensure_workspace_context()
    payload = fetch_analysis(analysis_id, workspace["workspace_id"])
    if not payload:
        return error_response("Analysis not found", status=404, code="analysis_not_found")
    return json_response(payload)
