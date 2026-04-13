from ..repositories.analysis_repository import (
    approve_analysis_version,
    analysis_record_to_payload,
    count_analysis_records,
    create_analysis_record,
    get_analysis_record,
    get_analysis_version,
    list_analysis_records,
    update_analysis_record,
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


def refine_analysis_record(analysis_id, workspace_id, result_ai_enhanced, new_prd, answers):
    record = get_analysis_record(analysis_id, workspace_id)
    if not record:
        return None
    result = dict(new_prd)
    result["ai_enhanced"] = result_ai_enhanced
    record = update_analysis_record(record, result_ai_enhanced, result.get("prd"), answers, result=result)
    return analysis_record_to_payload(record, version=get_analysis_version(record))


def fetch_analysis(analysis_id, workspace_id, version_selector="current", include_versions=False):
    record = get_analysis_record(analysis_id, workspace_id)
    if not record:
        return None
    version = None
    if version_selector == "approved":
        version = get_analysis_version(record, approved=True)
    elif isinstance(version_selector, int):
        version = get_analysis_version(record, version_number=version_selector)
    else:
        version = get_analysis_version(record)
    return analysis_record_to_payload(record, version=version, include_versions=include_versions)


def approve_analysis(analysis_id, workspace_id, version_number=None):
    record = get_analysis_record(analysis_id, workspace_id)
    if not record:
        return None
    version = approve_analysis_version(record, version_number=version_number)
    if not version:
        return None
    return analysis_record_to_payload(record, version=version, include_versions=True)


def fetch_analysis_history(workspace_id, limit=20, offset=0):
    total = count_analysis_records(workspace_id)
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
            "total": total,
            "has_more": offset + len(items) < total,
        },
    }
