import json

from ..extensions import db
from ..models import AnalysisRecord


def _serialize(value):
    return json.dumps(value, sort_keys=True)


def _deserialize(value, default):
    if not value:
        return default
    return json.loads(value)


def create_analysis_record(requirements, ai_enhance, ai_provider, result, request_id=None):
    record = AnalysisRecord(
        request_id=request_id,
        requirements_text=requirements,
        ai_enhance_requested=ai_enhance,
        ai_provider=ai_provider,
        domain=result["domain"],
        rms=result["rms"],
        implied_users_json=_serialize(result["implied_users"]),
        missing_features_json=_serialize(result["missing_features"]),
        clarification_questions_json=_serialize(result["clarification_questions"]),
        conflicts_json=_serialize(result["conflicts"]),
        prd_json=_serialize(result["prd"]),
        ai_enhanced_json=_serialize(result["ai_enhanced"]) if result.get("ai_enhanced") is not None else None,
    )
    db.session.add(record)
    db.session.commit()
    return record


def get_analysis_record(analysis_id):
    return db.session.get(AnalysisRecord, analysis_id)


def list_analysis_records(limit=20, offset=0):
    return (
        AnalysisRecord.query.order_by(AnalysisRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_analysis_records():
    return AnalysisRecord.query.count()


def analysis_record_to_payload(record):
    return {
        "analysis_id": record.id,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "request_id": record.request_id,
        "status": record.status,
        "requirements": record.requirements_text,
        "ai_enhance_requested": record.ai_enhance_requested,
        "ai_provider": record.ai_provider,
        "domain": record.domain,
        "rms": record.rms,
        "implied_users": _deserialize(record.implied_users_json, []),
        "missing_features": _deserialize(record.missing_features_json, []),
        "clarification_questions": _deserialize(record.clarification_questions_json, []),
        "conflicts": _deserialize(record.conflicts_json, []),
        "prd": _deserialize(record.prd_json, {}),
        "ai_enhanced": _deserialize(record.ai_enhanced_json, None),
    }
