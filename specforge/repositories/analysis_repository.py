import json

from ..extensions import db
from ..models import AnalysisRecord, AnalysisVersion


def _serialize(value):
    return json.dumps(value, sort_keys=True)


def _deserialize(value, default):
    if not value:
        return default
    return json.loads(value)


def _version_to_payload(version):
    if version is None:
        return None
    return {
        "version_number": version.version_number,
        "created_at": version.created_at.isoformat(),
        "updated_at": version.updated_at.isoformat(),
        "product_brief": _deserialize(version.product_brief_json, {}),
        "clarification_questions_v2": _deserialize(version.clarification_questions_json, []),
        "prd_document": _deserialize(version.prd_document_json, {}),
        "generation_run": _deserialize(version.generation_run_json, {}),
        "legacy_prd": _deserialize(version.legacy_prd_json, {}),
        "section_diffs": _deserialize(version.section_diffs_json, []),
        "approval_state": version.approval_state,
        "approved_at": version.approved_at.isoformat() if version.approved_at else None,
    }


def get_analysis_version(record, version_number=None, approved=False):
    query = AnalysisVersion.query.filter_by(analysis_id=record.id, workspace_id=record.workspace_id)
    if approved:
        if record.approved_version_number is None:
            return None
        query = query.filter_by(version_number=record.approved_version_number)
    elif version_number is not None:
        query = query.filter_by(version_number=version_number)
    else:
        query = query.filter_by(version_number=record.current_version_number or 1)
    return query.one_or_none()


def create_analysis_version(record, result, version_number, section_diffs=None, approval_state="draft", approved_at=None):
    version = AnalysisVersion(
        analysis_id=record.id,
        workspace_id=record.workspace_id,
        version_number=version_number,
        product_brief_json=_serialize(result.get("product_brief", {})),
        clarification_questions_json=_serialize(result.get("clarification_questions_v2", [])),
        prd_document_json=_serialize(result.get("prd_document", {})),
        generation_run_json=_serialize(result.get("generation_run", {})),
        legacy_prd_json=_serialize(result.get("prd", {})),
        section_diffs_json=_serialize(section_diffs or result.get("section_diffs", [])) if (section_diffs or result.get("section_diffs")) is not None else None,
        approval_state=approval_state,
        approved_at=approved_at,
    )
    db.session.add(version)
    return version


def create_analysis_record(requirements, ai_enhance, ai_provider, result, workspace_id, request_id=None):
    record = AnalysisRecord(
        workspace_id=workspace_id,
        request_id=request_id,
        requirements_text=requirements,
        ai_enhance_requested=ai_enhance,
        ai_provider=ai_provider,
        model=(result.get("generation_run") or {}).get("model"),
        intake_json=_serialize(result.get("product_brief", {})),
        domain=result["domain"],
        rms=result["rms"],
        implied_users_json=_serialize(result["implied_users"]),
        missing_features_json=_serialize(result["missing_features"]),
        clarification_questions_json=_serialize(result["clarification_questions"]),
        conflicts_json=_serialize(result["conflicts"]),
        prd_json=_serialize(result["prd"]),
        ai_enhanced_json=_serialize(result["ai_enhanced"]) if result.get("ai_enhanced") is not None else None,
        current_version_number=result.get("draft_version", 1),
        approved_version_number=result.get("approved_version"),
    )
    db.session.add(record)
    db.session.commit()
    create_analysis_version(
        record,
        result,
        version_number=result.get("draft_version", 1),
        section_diffs=result.get("section_diffs"),
        approval_state=result.get("approval_state", "draft"),
    )
    db.session.commit()
    return record


def get_analysis_record(analysis_id, workspace_id):
    return AnalysisRecord.query.filter_by(id=analysis_id, workspace_id=workspace_id).one_or_none()


def update_analysis_record(record, ai_enhanced, prd_json_dict=None, answers_dict=None, result=None):
    if ai_enhanced is not None:
        record.ai_enhanced_json = _serialize(ai_enhanced)
    if prd_json_dict is not None:
        record.prd_json = _serialize(prd_json_dict)
    if answers_dict is not None:
        record.answers_json = _serialize(answers_dict)
    if result is not None:
        record.domain = result.get("domain", record.domain)
        record.rms = result.get("rms", record.rms)
        record.intake_json = _serialize(result.get("product_brief", _deserialize(getattr(record, "intake_json", None), {})))
        record.implied_users_json = _serialize(result.get("implied_users", _deserialize(record.implied_users_json, [])))
        record.missing_features_json = _serialize(result.get("missing_features", _deserialize(record.missing_features_json, [])))
        record.clarification_questions_json = _serialize(result.get("clarification_questions", _deserialize(record.clarification_questions_json, [])))
        record.conflicts_json = _serialize(result.get("conflicts", _deserialize(record.conflicts_json, [])))
        record.model = ((result.get("generation_run") or {}).get("model")) or record.model
        record.current_version_number = result.get("draft_version", record.current_version_number or 1)
        record.approved_version_number = result.get("approved_version", record.approved_version_number)
        create_analysis_version(
            record,
            result,
            version_number=record.current_version_number,
            section_diffs=result.get("section_diffs"),
            approval_state=result.get("approval_state", "draft"),
            approved_at=None,
        )
    db.session.commit()
    return record


def approve_analysis_version(record, version_number=None):
    version = get_analysis_version(record, version_number=version_number)
    if version is None:
        return None
    version.approval_state = "approved"
    from ..models import utcnow

    version.approved_at = utcnow()
    record.approved_version_number = version.version_number
    db.session.commit()
    return version


def list_analysis_records(workspace_id, limit=20, offset=0):
    return (
        AnalysisRecord.query.filter_by(workspace_id=workspace_id)
        .order_by(AnalysisRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_analysis_records(workspace_id):
    return AnalysisRecord.query.filter_by(workspace_id=workspace_id).count()


def analysis_record_to_payload(record, version=None, include_versions=False):
    version_payload = _version_to_payload(version or get_analysis_version(record))
    payload = {
        "analysis_id": record.id,
        "workspace_id": record.workspace_id,
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
        "answers": _deserialize(getattr(record, "answers_json", None), {}),
        "draft_version": record.current_version_number or 1,
        "approved_version": record.approved_version_number,
        "approval_state": "approved" if record.approved_version_number == (record.current_version_number or 1) and record.approved_version_number is not None else "draft",
    }
    if version_payload:
        payload["product_brief"] = version_payload["product_brief"]
        payload["clarification_questions_v2"] = version_payload["clarification_questions_v2"]
        payload["prd_document"] = version_payload["prd_document"]
        payload["generation_run"] = version_payload["generation_run"]
        payload["section_diffs"] = version_payload["section_diffs"]
        payload["approval_state"] = version_payload["approval_state"]
        payload["approved_at"] = version_payload["approved_at"]
    else:
        payload.setdefault("product_brief", {})
        payload.setdefault("clarification_questions_v2", [])
        payload.setdefault("prd_document", {})
        payload.setdefault("generation_run", {})
        payload.setdefault("section_diffs", [])
        payload.setdefault("approved_at", None)
    if include_versions:
        versions = (
            AnalysisVersion.query.filter_by(analysis_id=record.id, workspace_id=record.workspace_id)
            .order_by(AnalysisVersion.version_number.asc())
            .all()
        )
        payload["versions"] = [_version_to_payload(item) for item in versions]
    return payload
