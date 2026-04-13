from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from flask import current_app
from sqlalchemy import text

from ..extensions import db
from ..models import AnalysisJob


def utcnow():
    return datetime.now(timezone.utc)


def ensure_aware(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


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


def check_migrations(config):
    migrations_dir = Path(config.get("MIGRATIONS_DIR", ""))
    expected = len(list(migrations_dir.glob("*.sql"))) if migrations_dir.exists() else 0
    try:
        applied = db.session.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar_one()
    except Exception as exc:  # pragma: no cover - exercised via readiness failure test
        db.session.rollback()
        return {
            "name": "migrations",
            "status": "down",
            "required": True,
            "message": "Migration metadata is not readable",
            "details": {"error": str(exc), "expected": expected, "applied": 0},
        }

    if applied < expected:
        return {
            "name": "migrations",
            "status": "down",
            "required": True,
            "message": "Database schema is behind the checked-in migrations",
            "details": {"expected": expected, "applied": applied},
        }

    return {
        "name": "migrations",
        "status": "ok",
        "required": True,
        "message": "Database schema matches checked-in migrations",
        "details": {"expected": expected, "applied": applied},
    }


def check_job_queue(backlog_warning_threshold=100, backlog_critical_threshold=500, failed_jobs_critical_threshold=25):
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
        oldest_job_age_seconds = int((utcnow() - ensure_aware(oldest_job.created_at)).total_seconds())

    status = "ok"
    message = "Job queue is healthy"
    if queued_jobs >= backlog_critical_threshold or failed_jobs >= failed_jobs_critical_threshold:
        status = "down"
        message = "Job queue requires operator action"
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
            "failed_jobs_critical_threshold": failed_jobs_critical_threshold,
        },
    }


def check_openrouter_provider_configuration(config):
    api_key = config.get("OPENROUTER_API_KEY", "")
    model = config.get("OPENROUTER_MODEL", "")
    site_url = config.get("OPENROUTER_SITE_URL", "")

    api_key_configured = bool(api_key)
    model_configured = bool(model)

    missing = []
    if not api_key:
        missing.append("OPENROUTER_API_KEY")
    if not model:
        missing.append("OPENROUTER_MODEL")

    status = "ok" if api_key_configured else "degraded"
    message = "OpenRouter provider configured" if status == "ok" else "OpenRouter provider is not fully configured"

    return {
        "name": "provider",
        "status": status,
        "required": False,
        "message": message,
        "details": {
            "api_key_configured": api_key_configured,
            "model_configured": model_configured,
            "site_url_configured": bool(site_url),
            "available_modes": ["api_key"] if api_key_configured else [],
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
    started_at = current_app.extensions.get("started_at", time.time())
    return {
        "status": "alive",
        "version": config.get("HEALTH_LIVENESS_VERSION", "2.0.0"),
        "uptime_seconds": round(max(0.0, time.time() - started_at), 3),
        "checks": [
            {"name": "process", "status": "ok", "required": True},
        ],
    }


def build_readiness_report(config):
    database = check_database()
    migrations = check_migrations(config)
    queue = check_job_queue(
        backlog_warning_threshold=config.get("HEALTH_QUEUE_BACKLOG_WARNING", 100),
        backlog_critical_threshold=config.get("HEALTH_QUEUE_BACKLOG_CRITICAL", 500),
        failed_jobs_critical_threshold=config.get("HEALTH_FAILED_JOBS_CRITICAL", 25),
    )
    provider = check_openrouter_provider_configuration(config)
    checks = [database, migrations, queue, provider]
    status = summarize_health(checks)
    ready = status != "down"
    return {
        "status": status,
        "ready": ready,
        "version": config.get("HEALTH_LIVENESS_VERSION", "2.0.0"),
        "checks": checks,
        "summary": {
            "database": database["status"],
            "migrations": migrations["status"],
            "queue": queue["status"],
            "provider": provider["status"],
        },
    }
