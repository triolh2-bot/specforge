from ..repositories.analysis_repository import (
    analysis_record_to_payload,
    count_analysis_records,
    create_analysis_record,
    get_analysis_record,
    list_analysis_records,
)
def persist_analysis(requirements, ai_enhance, ai_provider, result, workspace_id, request_id=None):
    record = create_analysis_record(
        requirements,
        ai_enhance,
        ai_provider,
        result,
        workspace_id=workspace_id,
        request_id=request_id,
    )
    stored = analysis_record_to_payload(record)
    result["analysis_id"] = stored["analysis_id"]
    result["workspace_id"] = stored["workspace_id"]
    result["created_at"] = stored["created_at"]
    result["updated_at"] = stored["updated_at"]
    return result


def fetch_analysis(analysis_id, workspace_id):
    record = get_analysis_record(analysis_id, workspace_id)
    if not record:
        return None
    return analysis_record_to_payload(record)


def fetch_analysis_history(workspace_id, limit=20, offset=0):
    records = list_analysis_records(workspace_id, limit=limit, offset=offset)
    items = [
        {
            "analysis_id": record.id,
            "workspace_id": record.workspace_id,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "domain": record.domain,
            "rms": record.rms,
            "status": record.status,
            "requirements_preview": record.requirements_text[:160],
            "ai_enhance_requested": record.ai_enhance_requested,
            "ai_provider": record.ai_provider,
        }
        for record in records
    ]
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": count_analysis_records(workspace_id),
        },
    }
