from flask import Blueprint, current_app, g, render_template

from ..http import json_response
from ..services.auth_session import ensure_workspace_context
from ..services.abuse import rate_limit
from ..services.analysis_store import persist_analysis
from ..services.health import build_liveness_report, build_readiness_report
from ..services.job_queue import enqueue_analysis_job
from ..services.prd import generate_prd
from ..validation import validate_analyze_request

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/analyze", methods=["POST"])
@rate_limit("analyze")
def analyze():
    data = validate_analyze_request()
    workspace = ensure_workspace_context()
    if data["ai_enhance"]:
        job = enqueue_analysis_job(
            data["requirements"],
            data["ai_enhance"],
            data["ai_provider"],
            workspace_id=workspace["workspace_id"],
            request_id=getattr(g, "request_id", None),
        )
        return json_response(
            {
                "success": True,
                "job_id": job["job_id"],
                "status": job["status"],
                "queued": True,
                "workspace_id": workspace["workspace_id"],
            },
            status=202,
        )

    result = generate_prd(data["requirements"], data["ai_enhance"], data["ai_provider"])
    result = persist_analysis(
        data["requirements"],
        data["ai_enhance"],
        data["ai_provider"],
        result,
        workspace_id=workspace["workspace_id"],
        request_id=getattr(g, "request_id", None),
    )
    return json_response(result)


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
