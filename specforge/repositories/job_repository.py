import json
from datetime import timedelta

from sqlalchemy import select, update

from ..extensions import db
from ..models import AnalysisJob, utcnow


def _serialize(value):
    return json.dumps(value, sort_keys=True)


def _deserialize(value, default=None):
    if not value:
        return default
    return json.loads(value)


def create_job(
    requirements,
    ai_enhance,
    ai_provider,
    workspace_id,
    request_id=None,
    max_attempts=3,
    model=None,
    intake_fields=None,
    quota_reservations=None,
):
    job = AnalysisJob(
        workspace_id=workspace_id,
        request_id=request_id,
        requirements_text=requirements,
        ai_enhance_requested=ai_enhance,
        ai_provider=ai_provider,
        model=model,
        intake_json=_serialize(intake_fields) if intake_fields is not None else None,
        quota_reservations_json=_serialize(quota_reservations) if quota_reservations is not None else None,
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
    # Compare-and-swap style claim avoids double-processing when multiple workers race.
    for _ in range(5):
        query = (
            select(AnalysisJob.id)
            .where(AnalysisJob.status == "queued")
            .order_by(AnalysisJob.created_at.asc())
            .limit(1)
        )
        job_id = db.session.execute(query).scalar_one_or_none()
        if not job_id:
            return None

        now = utcnow()
        result = db.session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id, AnalysisJob.status == "queued")
            .values(
                status="running",
                started_at=now,
                updated_at=now,
                attempt_count=AnalysisJob.attempt_count + 1,
            )
        )
        if result.rowcount:
            db.session.commit()
            return AnalysisJob.query.filter_by(id=job_id).one_or_none()
        db.session.rollback()
    return None


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


def reset_stale_jobs(stale_minutes=15, max_attempts=3):
    """Return jobs stuck in running state back to queued."""
    if stale_minutes <= 0:
        return 0
    cutoff = utcnow() - timedelta(minutes=stale_minutes)
    stale_jobs = (
        AnalysisJob.query.filter(AnalysisJob.status == "running", AnalysisJob.started_at.isnot(None))
        .filter(AnalysisJob.started_at < cutoff)
        .filter(AnalysisJob.attempt_count < max_attempts)
        .all()
    )
    for job in stale_jobs:
        job.status = "queued"
        job.updated_at = utcnow()
        job.error_message = "Recovered from stale running state"
    if stale_jobs:
        db.session.commit()
    return len(stale_jobs)


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
        "model": job.model,
        "intake_fields": _deserialize(getattr(job, "intake_json", None), None),
        "quota_reservations": _deserialize(getattr(job, "quota_reservations_json", None), None),
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": _deserialize(job.result_json),
    }
