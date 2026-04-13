from flask import Blueprint, request

from ..http import error_response, json_response
from ..services.abuse import rate_limit
from ..services.auth_session import ensure_workspace_context
from ..services.analysis_store import approve_analysis, fetch_analysis, fetch_analysis_history
from ..services.rbac import PERM, enforce_resource_access

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
    enforce_resource_access(workspace["workspace_id"], PERM.READ_ANALYSIS.name)

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
    enforce_resource_access(workspace["workspace_id"], PERM.READ_ANALYSIS.name)

    version_arg = request.args.get("version")
    include_versions = request.args.get("include_versions", "").lower() in {"1", "true", "yes"}
    version_selector = "current"
    if version_arg == "approved":
        version_selector = "approved"
    elif version_arg:
        try:
            version_selector = int(version_arg)
        except ValueError:
            return error_response("Query parameter 'version' must be an integer or 'approved'", status=400, code="invalid_query_parameter")

    payload = fetch_analysis(analysis_id, workspace["workspace_id"], version_selector=version_selector, include_versions=include_versions)
    if not payload:
        return error_response("Analysis not found", status=404, code="analysis_not_found")
    return json_response(payload)


@analyses_bp.route("/api/analyses/<analysis_id>/approve", methods=["POST"])
@rate_limit("analyze")
def approve_analysis_version_route(analysis_id):
    workspace = ensure_workspace_context()
    enforce_resource_access(workspace["workspace_id"], PERM.WRITE_ANALYSIS.name)

    data = request.get_json(silent=True) or {}
    version_number = data.get("version_number")
    if version_number is not None and not isinstance(version_number, int):
        return error_response("'version_number' must be an integer", status=400, code="invalid_field_type")

    payload = approve_analysis(analysis_id, workspace["workspace_id"], version_number=version_number)
    if not payload:
        return error_response("Analysis version not found", status=404, code="analysis_version_not_found")
    return json_response(payload)
