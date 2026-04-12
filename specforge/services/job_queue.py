import time

from ..repositories.job_repository import (
    claim_next_queued_job,
    create_job,
    get_job,
    job_to_payload,
    mark_job_completed,
    mark_job_failed,
)
from .analysis_store import persist_analysis
from .observability import record_job_metric
from .prd import generate_prd


def enqueue_analysis_job(requirements, ai_enhance, ai_provider, workspace_id, request_id=None):
    job = create_job(requirements, ai_enhance, ai_provider, workspace_id=workspace_id, request_id=request_id)
    return job_to_payload(job)


def fetch_job(job_id, workspace_id):
    job = get_job(job_id, workspace_id=workspace_id)
    if not job:
        return None
    return job_to_payload(job)


def process_job(job):
    started_at = time.perf_counter()
    result = generate_prd(job.requirements_text, job.ai_enhance_requested, job.ai_provider or "minimax")
    result = persist_analysis(
        job.requirements_text,
        job.ai_enhance_requested,
        job.ai_provider or "minimax",
        result,
        workspace_id=job.workspace_id,
        request_id=job.request_id,
    )
    updated_job = mark_job_completed(job, result["analysis_id"], result)
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    record_job_metric("completed", duration_ms=duration_ms, job_id=job.id, analysis_id=result["analysis_id"])
    return job_to_payload(updated_job)


def process_next_job():
    job = claim_next_queued_job()
    if not job:
        return None
    try:
        return process_job(job)
    except Exception as error:
        mark_job_failed(job, str(error))
        record_job_metric("failed", job_id=job.id)
        raise


def worker_loop(poll_interval=1.0, max_jobs=None, shutdown_flag=None):
    """Process queued jobs until *max_jobs* is reached or *shutdown_flag* is set.

    Parameters
    ----------
    poll_interval:
        Seconds to sleep when the queue is empty.
    max_jobs:
        Optional cap on jobs to process (useful for tests).
    shutdown_flag:
        Optional callable returning ``True`` when the worker should exit
        after completing its current job.
    """
    processed = 0
    while True:
        if shutdown_flag and shutdown_flag():
            return processed
        job = process_next_job()
        if job is None:
            if max_jobs is not None and processed >= max_jobs:
                return processed
            time.sleep(poll_interval)
            continue
        processed += 1
        if max_jobs is not None and processed >= max_jobs:
            return processed
