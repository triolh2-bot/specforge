"""Admin operations and support tooling routes.

Provides internal views for:
- User/workspace lookup
- Job inspection and replay
- Failed export inspection
- Provider incident review
- Abuse case management
- Operator action logging
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, request

from ..extensions import db
from ..http import error_response, json_response
from ..models import (
    AnalysisJob,
    AnalysisRecord,
    ExportRecord,
    ProductEvent,
    QuotaUsage,
    Workspace,
    WorkspaceSubscription,
)
from ..services.auth_session import ensure_workspace_context
from ..services.job_queue import process_job
from ..services.rbac import require_role

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------

def _require_admin():
    """Ensure the current user has admin or owner role."""
    from flask import session
    role = session.get("workspace_role")
    if role not in ("admin", "owner"):
        from ..services.rbac import AuthorizationError
        raise AuthorizationError(
            permission="admin_access",
            required_role="admin",
            actual_role=role or "anonymous",
            message="Admin or owner role required",
        )


# ---------------------------------------------------------------------------
# Workspace and user lookup
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/workspaces", methods=["GET"])
@require_role("admin")
def admin_list_workspaces():
    """List all workspaces with subscription status."""
    limit = min(request.args.get("limit", 50, type=int), 200)
    offset = max(request.args.get("offset", 0, type=int), 0)

    query = Workspace.query
    total = query.count()
    workspaces = query.order_by(Workspace.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for ws in workspaces:
        sub = WorkspaceSubscription.query.filter_by(workspace_id=ws.id).first()
        items.append({
            "workspace_id": ws.id,
            "name": ws.name,
            "created_at": ws.created_at.isoformat(),
            "subscription": {
                "plan": sub.plan if sub else "free",
                "status": sub.status if sub else "none",
                "provider": sub.provider if sub else None,
            } if sub else {"plan": "free", "status": "none"},
        })

    return json_response({
        "workspaces": items,
        "pagination": {"limit": limit, "offset": offset, "total": total},
    })


@admin_bp.route("/api/admin/workspaces/<workspace_id>", methods=["GET"])
@require_role("admin")
def admin_get_workspace(workspace_id: str):
    """Get detailed workspace info including members, usage, and subscription."""
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return error_response("Workspace not found", status=404, code="workspace_not_found")

    # Count analyses
    analysis_count = AnalysisRecord.query.filter_by(workspace_id=workspace_id).count()
    export_count = ExportRecord.query.filter_by(workspace_id=workspace_id).count()
    recent_events = ProductEvent.query.filter_by(workspace_id=workspace_id).order_by(
        ProductEvent.occurred_at.desc()
    ).limit(10).all()

    return json_response({
        "workspace_id": workspace.id,
        "name": workspace.name,
        "created_at": workspace.created_at.isoformat(),
        "stats": {
            "analyses": analysis_count,
            "exports": export_count,
            "recent_events": [
                {
                    "name": ev.name,
                    "category": ev.category,
                    "occurred_at": ev.occurred_at.isoformat(),
                }
                for ev in recent_events
            ],
        },
    })


# ---------------------------------------------------------------------------
# Job inspection and replay
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/jobs", methods=["GET"])
@require_role("admin")
def admin_list_jobs():
    """List jobs with filtering options."""
    status_filter = request.args.get("status")
    workspace_id = request.args.get("workspace_id")
    limit = min(request.args.get("limit", 50, type=int), 200)
    offset = max(request.args.get("offset", 0, type=int), 0)

    query = AnalysisJob.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    total = query.count()
    jobs = query.order_by(AnalysisJob.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for job in jobs:
        items.append({
            "job_id": job.id,
            "workspace_id": job.workspace_id,
            "status": job.status,
            "attempt_count": job.attempt_count,
            "max_attempts": job.max_attempts,
            "ai_provider": job.ai_provider,
            "ai_enhance_requested": job.ai_enhance_requested,
            "requirements_preview": job.requirements_text[:120] if job.requirements_text else "",
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        })

    return json_response({
        "jobs": items,
        "pagination": {"limit": limit, "offset": offset, "total": total},
    })


@admin_bp.route("/api/admin/jobs/<job_id>/replay", methods=["POST"])
@require_role("admin")
def admin_replay_job(job_id: str):
    """Replay a failed job. Resets attempt count and re-queues."""
    job = AnalysisJob.query.get(job_id)
    if not job:
        return error_response("Job not found", status=404, code="job_not_found")

    if job.status not in ("failed", "completed"):
        return error_response(
            f"Cannot replay job in '{job.status}' state. Only failed or completed jobs can be replayed.",
            status=400,
            code="invalid_job_state",
        )

    job.status = "queued"
    job.attempt_count = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.result_json = None
    job.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return json_response({
        "job_id": job.id,
        "status": "queued",
        "message": "Job re-queued for replay",
    })


# ---------------------------------------------------------------------------
# Export inspection
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/exports", methods=["GET"])
@require_role("admin")
def admin_list_exports():
    """List exports with filtering for failed or stale exports."""
    workspace_id = request.args.get("workspace_id")
    failed_only = request.args.get("failed", "false").lower() == "true"
    limit = min(request.args.get("limit", 50, type=int), 200)

    query = ExportRecord.query
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    exports = query.order_by(ExportRecord.created_at.desc()).limit(limit).all()

    items = []
    for exp in exports:
        items.append({
            "export_id": exp.id,
            "workspace_id": exp.workspace_id,
            "analysis_id": exp.analysis_id,
            "format": exp.export_format,
            "filename": exp.filename,
            "content_length": exp.content_length,
            "download_count": exp.download_count,
            "share_token": exp.share_token[:8] + "..." if exp.share_token else None,
            "created_at": exp.created_at.isoformat(),
        })

    return json_response({"exports": items, "count": len(items)})


# ---------------------------------------------------------------------------
# Quota inspection
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/quota/usage", methods=["GET"])
@require_role("admin")
def admin_quota_usage():
    """View quota usage across workspaces."""
    workspace_id = request.args.get("workspace_id")
    days = min(request.args.get("days", 7, type=int), 365)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = QuotaUsage.query.filter(QuotaUsage.used_at >= since)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    usages = query.all()

    # Aggregate by workspace and metric
    aggregated: dict[str, dict[str, int]] = {}
    for u in usages:
        if u.workspace_id not in aggregated:
            aggregated[u.workspace_id] = {}
        aggregated[u.workspace_id][u.metric] = aggregated[u.workspace_id].get(u.metric, 0) + u.amount

    return json_response({
        "usage": aggregated,
        "period_days": days,
    })
