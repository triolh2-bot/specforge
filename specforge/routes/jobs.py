from flask import Blueprint

from ..http import error_response, json_response
from ..services.abuse import rate_limit
from ..services.auth_session import ensure_workspace_context
from ..services.job_queue import fetch_job

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/api/jobs/<job_id>", methods=["GET"])
@rate_limit("get_job")
def get_job(job_id):
    workspace = ensure_workspace_context()
    payload = fetch_job(job_id, workspace["workspace_id"])
    if not payload:
        return error_response("Job not found", status=404, code="job_not_found")
    return json_response(payload)
