from flask import Blueprint, current_app, g, render_template, session

from ..http import json_response
from ..services.analytics import (
    EventName,
    track_analysis_completed,
    track_analysis_failed,
    track_analysis_started,
    track_export_completed,
    track_funnel_event,
    track_provider_selected,
    track_session_event,
)
from ..services.auth_session import ensure_workspace_context
from ..services.abuse import rate_limit
from ..services.analysis_store import fetch_analysis_history, persist_analysis, fetch_analysis, refine_analysis_record
from ..services.billing import check_provider_allowed, consume_quota, QuotaExceededError
from ..services.health import build_liveness_report, build_readiness_report
from ..services.job_queue import enqueue_analysis_job
from ..services.prd import generate_prd, generate_refined_prd, generate_brief
from ..validation import validate_analyze_request, validate_refine_request
from ..repositories.analysis_repository import count_analysis_records

main_bp = Blueprint("main", __name__)


def _check_first_analysis(workspace_id: str) -> bool:
    """Return True if this workspace has never completed an analysis before.

    Uses a direct COUNT query to avoid race conditions with the pagination-
    based history lookup.
    """
    return count_analysis_records(workspace_id) == 0


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/analyze", methods=["POST"])
@rate_limit("analyze")
def analyze():
    data = validate_analyze_request()
    workspace = ensure_workspace_context()
    workspace_id = workspace["workspace_id"]
    request_id = getattr(g, "request_id", None)

    # Check provider is allowed by plan
    if not check_provider_allowed(workspace_id, data["ai_provider"]):
        return json_response(
            {
                "success": False,
                "error": {
                    "code": "provider_not_allowed",
                    "message": f"Provider '{data['ai_provider']}' is not available on your current plan.",
                },
            },
            status=403,
        )

    # Check and consume analysis quota
    try:
        consume_quota(workspace_id, "analysis")
        if data["ai_enhance"]:
            consume_quota(workspace_id, "ai_enhancement")
    except QuotaExceededError as exc:
        return json_response(
            {
                "success": False,
                "error": {
                    "code": "quota_exceeded",
                    "message": str(exc),
                    "metric": exc.metric,
                    "limit": exc.limit,
                    "plan": exc.plan,
                },
            },
            status=429,
        )

    # Track analysis started
    track_analysis_started(
        workspace_id=workspace_id,
        ai_provider=data["ai_provider"],
        use_ai=data["ai_enhance"],
        request_id=request_id,
    )

    # Track provider selection
    track_provider_selected(workspace_id=workspace_id, provider=data["ai_provider"], request_id=request_id)

    if data["ai_enhance"]:
        job = enqueue_analysis_job(
            data["requirements"],
            data["ai_enhance"],
            data["ai_provider"],
            workspace_id=workspace_id,
            request_id=request_id,
        )
        return json_response(
            {
                "success": True,
                "job_id": job["job_id"],
                "status": job["status"],
                "queued": True,
                "workspace_id": workspace_id,
            },
            status=202,
        )

    try:
        result = generate_prd(data["requirements"], data["ai_enhance"], data["ai_provider"])
        result = persist_analysis(
            data["requirements"],
            data["ai_enhance"],
            data["ai_provider"],
            result,
            workspace_id=workspace_id,
            request_id=request_id,
        )

        # Track completion
        track_analysis_completed(
            workspace_id=workspace_id,
            analysis_id=result["analysis_id"],
            domain=result.get("domain", "unknown"),
            rms=result.get("rms", 0),
            ai_provider=data["ai_provider"],
            ai_enhanced=data["ai_enhance"],
            request_id=request_id,
        )

        # Track first analysis (funnel)
        is_first = _check_first_analysis(workspace_id)
        track_session_event(workspace_id=workspace_id, is_first_analysis=is_first, request_id=request_id)

        return json_response(result)
    except Exception as exc:
        track_analysis_failed(workspace_id=workspace_id, error=str(exc), request_id=request_id)
        raise


@main_bp.route("/analyze/refine", methods=["POST"])
@rate_limit("analyze")
def refine_analysis():
    data = validate_refine_request()
    workspace = ensure_workspace_context()
    workspace_id = workspace["workspace_id"]
    request_id = getattr(g, "request_id", None)
    
    analysis_id = data["analysis_id"]
    answers = data["answers"]
    ai_provider = data["ai_provider"]

    if not check_provider_allowed(workspace_id, ai_provider):
        return json_response(
            {
                "success": False,
                "error": {
                    "code": "provider_not_allowed",
                    "message": f"Provider '{ai_provider}' is not available on your current plan.",
                },
            },
            status=403,
        )

    try:
        consume_quota(workspace_id, "ai_enhancement")
    except QuotaExceededError as exc:
        return json_response(
            {
                "success": False,
                "error": {
                    "code": "quota_exceeded",
                    "message": str(exc),
                    "metric": exc.metric,
                    "limit": exc.limit,
                    "current": exc.current,
                    "plan": exc.plan,
                },
            },
            status=429,
        )

    existing_analysis = fetch_analysis(analysis_id, workspace_id)
    if not existing_analysis:
        return json_response(
            {"success": False, "error": {"code": "not_found", "message": "Analysis not found"}},
            status=404,
        )

    try:
        updated_ai_status = generate_refined_prd(
            existing_analysis["requirements"],
            existing_analysis.get("domain", "unknown"),
            answers,
            ai_provider=ai_provider
        )
        
        # Build new PRD by merging
        old_prd = existing_analysis.get("prd", {})
        new_prd = dict(old_prd)
        
        if updated_ai_status and updated_ai_status["status"] == "success":
            ai_data = updated_ai_status["data"]
            
            if "overview" in new_prd:
                new_prd["overview"]["summary"] = ai_data.get("prd_summary", new_prd["overview"]["summary"])
            else:
                new_prd["overview"] = {"summary": ai_data.get("prd_summary", "")}
            
            if "technical_constraints" in new_prd:
                new_prd["technical_constraints"]["tech_stack"] = ai_data.get("tech_stack_recommendation", new_prd["technical_constraints"].get("tech_stack"))
                new_prd["technical_constraints"]["timeline"] = ai_data.get("estimated_timeline", new_prd["technical_constraints"].get("timeline"))
            else:
                new_prd["technical_constraints"] = {
                    "tech_stack": ai_data.get("tech_stack_recommendation", ""),
                    "timeline": ai_data.get("estimated_timeline", "")
                }
            
            if ai_data.get("risk_factors"):
                new_prd["risks"] = ai_data["risk_factors"]

        result = refine_analysis_record(analysis_id, workspace_id, updated_ai_status, new_prd, answers)

        return json_response(result)
    except Exception as exc:
        raise


@main_bp.route("/api/generate-brief", methods=["POST"])
@rate_limit("analyze")
def generate_brief_route():
    from ..validation import parse_json_object, require_string, optional_string
    data = parse_json_object()
    workspace = ensure_workspace_context()
    workspace_id = workspace["workspace_id"]

    project_name  = require_string(data, "project_name", min_length=2, max_length=200)
    project_type  = optional_string(data, "project_type", default="Web Application", max_length=100)
    core_idea     = require_string(data, "core_idea", min_length=10, max_length=2000)
    target_audience = optional_string(data, "target_audience", default="General users", max_length=300)
    key_features  = optional_string(data, "key_features", default="", max_length=2000)
    ai_provider   = optional_string(data, "ai_provider", default="openrouter",
                                    allowed_values={"minimax", "openrouter"})

    if not check_provider_allowed(workspace_id, ai_provider):
        return json_response(
            {"success": False, "error": {"code": "provider_not_allowed",
             "message": f"Provider '{ai_provider}' is not available on your plan."}},
            status=403,
        )

    result = generate_brief(
        project_name=project_name,
        project_type=project_type,
        core_idea=core_idea,
        target_audience=target_audience,
        key_features=key_features,
        ai_provider=ai_provider,
    )
    status = 200 if result["success"] else 502
    return json_response(result, status=status)


@main_bp.route("/health", methods=["GET"])
def health():
    payload = build_readiness_report(current_app.config)
    payload["endpoint"] = "/health"
    payload["mode"] = "compatibility"
    status_code = 200 if payload["ready"] else 503
    return json_response(payload, status=status_code)


@main_bp.route("/health/live", methods=["GET"])
def health_live():
    payload = build_liveness_report(current_app.config)
    payload["endpoint"] = "/health/live"
    return json_response(payload)


@main_bp.route("/health/ready", methods=["GET"])
def health_ready():
    payload = build_readiness_report(current_app.config)
    payload["endpoint"] = "/health/ready"
    status_code = 200 if payload["ready"] else 503
    return json_response(payload, status=status_code)
