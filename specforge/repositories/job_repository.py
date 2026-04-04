import json

from sqlalchemy import select

from ..extensions import db
from ..models import AnalysisJob, utcnow


def _serialize(value):
    return json.dumps(value, sort_keys=True)


def _deserialize(value, default=None):
    if not value:
        return default
    return json.loads(value)


def create_job(requirements, ai_enhance, ai_provider, workspace_id, request_id=None, max_attempts=3):
    job = AnalysisJob(
        workspace_id=workspace_id,
        request_id=request_id,
        requirements_text=requirements,
        ai_enhance_requested=ai_enhance,
        ai_provider=ai_provider,
        max_attempts=max_attempts,
        status="queued",
    )
    db.session.add(job)
    db.session.commit()
    return job


def get_job(job_id, workspace_id=None):
    query = AnalysisJob.query.filter_by(id=job_id)
    if workspace_id is not None:
        query = query.filter_by(workspace_id=workspace_id)
    return query.one_or_none()


def claim_next_queued_job():
    query = (
        select(AnalysisJob)
        .where(AnalysisJob.status == "queued")
        .order_by(AnalysisJob.created_at.asc())
        .limit(1)
    )
    job = db.session.execute(query).scalar_one_or_none()
    if not job:
        return None

    job.status = "running"
    job.started_at = utcnow()
    job.updated_at = utcnow()
    job.attempt_count += 1
    db.session.commit()
    return job


def mark_job_completed(job, analysis_id, result):
    job.status = "completed"
    job.analysis_id = analysis_id
    job.result_json = _serialize(result)
    job.error_message = None
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    db.session.commit()
    return job


def mark_job_failed(job, error_message):
    job.error_message = error_message
    if job.attempt_count < job.max_attempts:
        job.status = "queued"
    else:
        job.status = "failed"
        job.completed_at = utcnow()
    job.updated_at = utcnow()
    db.session.commit()
    return job


def job_to_payload(job):
    return {
        "job_id": job.id,
        "workspace_id": job.workspace_id,
        "status": job.status,
        "request_id": job.request_id,
        "analysis_id": job.analysis_id,
        "requirements": job.requirements_text,
        "ai_enhance_requested": job.ai_enhance_requested,
        "ai_provider": job.ai_provider,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": _deserialize(job.result_json),
    }
