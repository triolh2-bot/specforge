from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text

from ..extensions import db
from ..models import AnalysisJob


def utcnow():
    return datetime.now(timezone.utc)


def check_database():
    try:
        db.session.execute(text("SELECT 1"))
        return {"name": "database", "status": "ok", "required": True}
    except Exception as exc:  # pragma: no cover - exercised via readiness failure test
        db.session.rollback()
        return {
            "name": "database",
            "status": "down",
            "required": True,
            "message": "Database connection failed",
            "details": {"error": str(exc)},
        }


def check_job_queue(backlog_warning_threshold=100, backlog_critical_threshold=500):
    try:
        queued_jobs = AnalysisJob.query.filter_by(status="queued").count()
        running_jobs = AnalysisJob.query.filter_by(status="running").count()
        failed_jobs = AnalysisJob.query.filter_by(status="failed").count()
        oldest_job = AnalysisJob.query.filter_by(status="queued").order_by(AnalysisJob.created_at.asc()).first()
    except Exception as exc:  # pragma: no cover - covered through readiness failure path
        db.session.rollback()
        return {
            "name": "queue",
            "status": "down",
            "required": True,
            "message": "Job queue is not queryable",
            "details": {"error": str(exc)},
        }

    oldest_job_age_seconds = None
    if oldest_job and oldest_job.created_at:
        oldest_job_age_seconds = int((utcnow() - oldest_job.created_at).total_seconds())

    status = "ok"
    message = "Job queue is healthy"
    if queued_jobs >= backlog_critical_threshold:
        status = "down"
        message = "Job queue backlog is critical"
    elif queued_jobs >= backlog_warning_threshold:
        status = "degraded"
        message = "Job queue backlog is elevated"

    return {
        "name": "queue",
        "status": status,
        "required": True,
        "message": message,
        "details": {
            "queued_jobs": queued_jobs,
            "running_jobs": running_jobs,
            "failed_jobs": failed_jobs,
            "oldest_queued_job_age_seconds": oldest_job_age_seconds,
            "warning_threshold": backlog_warning_threshold,
            "critical_threshold": backlog_critical_threshold,
        },
    }


def check_minimax_provider_configuration(config):
    oauth_fields = [
        config.get("MINIMAX_CLIENT_ID", ""),
        config.get("MINIMAX_CLIENT_SECRET", ""),
        config.get("MINIMAX_REDIRECT_URI", ""),
    ]
    api_key = config.get("MINIMAX_API_KEY", "")
    oauth_configured = all(field for field in oauth_fields)
    api_key_configured = bool(api_key)

    missing = []
    if not oauth_configured:
        if not config.get("MINIMAX_CLIENT_ID", ""):
            missing.append("MINIMAX_CLIENT_ID")
        if not config.get("MINIMAX_CLIENT_SECRET", ""):
            missing.append("MINIMAX_CLIENT_SECRET")
        if not config.get("MINIMAX_REDIRECT_URI", ""):
            missing.append("MINIMAX_REDIRECT_URI")

    status = "ok" if oauth_configured or api_key_configured else "degraded"
    message = "MiniMax provider configured" if status == "ok" else "MiniMax provider is not fully configured"

    return {
        "name": "provider",
        "status": status,
        "required": False,
        "message": message,
        "details": {
            "oauth_configured": oauth_configured,
            "api_key_configured": api_key_configured,
            "available_modes": [mode for mode, enabled in (("oauth", oauth_configured), ("api_key", api_key_configured)) if enabled],
            "missing_fields": missing,
        },
    }


def summarize_health(checks):
    required_checks = [check for check in checks if check.get("required")]
    if any(check["status"] == "down" for check in required_checks):
        return "down"
    if any(check["status"] == "degraded" for check in required_checks):
        return "degraded"
    return "ok"


def build_liveness_report(config):
    return {
        "status": "alive",
        "version": config.get("HEALTH_LIVENESS_VERSION", "2.0.0"),
        "checks": [
            {"name": "process", "status": "ok", "required": True},
        ],
    }


def build_readiness_report(config):
    database = check_database()
    queue = check_job_queue(
        backlog_warning_threshold=config.get("HEALTH_QUEUE_BACKLOG_WARNING", 100),
        backlog_critical_threshold=config.get("HEALTH_QUEUE_BACKLOG_CRITICAL", 500),
    )
    provider = check_minimax_provider_configuration(config)
    checks = [database, queue, provider]
    status = summarize_health(checks)
    ready = status != "down"
    return {
        "status": status,
        "ready": ready,
        "version": config.get("HEALTH_LIVENESS_VERSION", "2.0.0"),
        "checks": checks,
        "summary": {
            "database": database["status"],
            "queue": queue["status"],
            "provider": provider["status"],
        },
    }
