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
from ..services.analysis_store import fetch_analysis_history, persist_analysis
from ..services.billing import check_provider_allowed, consume_quota, QuotaExceededError
from ..services.health import build_liveness_report, build_readiness_report
from ..services.job_queue import enqueue_analysis_job
from ..services.prd import generate_prd
from ..validation import validate_analyze_request
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
