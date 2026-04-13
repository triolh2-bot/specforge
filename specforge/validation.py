from flask import request

from .contracts import AIChatRequest, AIEnhanceRequest, AnalyzeRequest


class ValidationError(Exception):
    def __init__(self, message, status_code=400, code="validation_error", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


def parse_json_object():
    if not request.is_json:
        raise ValidationError(
            "Request must use Content-Type: application/json",
            status_code=415,
            code="unsupported_media_type",
        )

    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError("Request body must contain valid JSON", code="invalid_json")
    if not isinstance(data, dict):
        raise ValidationError("JSON body must be an object", code="invalid_payload")
    return data


def validate_analyze_request() -> AnalyzeRequest:
    data = parse_json_object()
    requirements = optional_string(data, "requirements", default="", max_length=10000)
    structured_fields = {
        "target_users": optional_string(data, "target_users", default="", max_length=500) or None,
        "business_goal": optional_string(data, "business_goal", default="", max_length=1000) or None,
        "success_metrics": optional_string(data, "success_metrics", default="", max_length=1000) or None,
        "constraints": optional_string(data, "constraints", default="", max_length=1000) or None,
        "integrations": optional_string(data, "integrations", default="", max_length=1000) or None,
        "compliance": optional_string(data, "compliance", default="", max_length=500) or None,
        "monetization": optional_string(data, "monetization", default="", max_length=500) or None,
        "timeline": optional_string(data, "timeline", default="", max_length=300) or None,
        "budget": optional_string(data, "budget", default="", max_length=300) or None,
        "scope_notes": optional_string(data, "scope_notes", default="", max_length=1000) or None,
    }
    if requirements and len(requirements) < 10:
        raise ValidationError(
            "'requirements' must be at least 10 characters",
            code="field_too_short",
            details={"field": "requirements", "min_length": 10},
        )
    if not requirements and not any(structured_fields.values()):
        raise ValidationError(
            "Provide either requirements text or at least one structured intake field",
            code="missing_field",
            details={"field": "requirements"},
        )
    return {
        "requirements": requirements,
        "ai_enhance": optional_bool(data, "ai_enhance", default=False),
        "ai_provider": optional_string(data, "ai_provider", default="openrouter", allowed_values={"openrouter"}),
        "model": optional_string(data, "model", default="", max_length=100) or None,
        **structured_fields,
    }


def validate_refine_request() -> dict:
    data = parse_json_object()
    answers = data.get("answers")
    valid_answers = {}
    answer_items = []
    if isinstance(answers, dict):
        valid_answers = {k: v for k, v in answers.items() if isinstance(v, str) and v.strip()}
        answer_items = [{"question_id": None, "question": k, "answer": v} for k, v in valid_answers.items()]
    elif isinstance(answers, list):
        for item in answers:
            if not isinstance(item, dict):
                continue
            question_id = item.get("question_id")
            answer = item.get("answer")
            question = item.get("question")
            if isinstance(answer, str) and answer.strip():
                answer_items.append({
                    "question_id": question_id if isinstance(question_id, str) and question_id.strip() else None,
                    "question": question if isinstance(question, str) and question.strip() else None,
                    "answer": answer.strip(),
                })
        valid_answers = {
            (item["question_id"] or item["question"]): item["answer"]
            for item in answer_items if item["question_id"] or item["question"]
        }
    else:
        raise ValidationError("'answers' must be a JSON object or array", code="invalid_field_type", details={"field": "answers"})

    if not valid_answers:
        raise ValidationError("At least one answer must be provided", code="missing_answers")

    return {
        "analysis_id": require_string(data, "analysis_id", min_length=36, max_length=36),
        "answers": valid_answers,
        "answer_items": answer_items,
        "ai_provider": optional_string(data, "ai_provider", default="openrouter", allowed_values={"openrouter"}),
        "model": optional_string(data, "model", default="", max_length=100) or None,
        "version_number": optional_int(data, "version_number", default=None),
    }


def validate_ai_chat_request() -> AIChatRequest:
    data = parse_json_object()
    return {
        "message": require_string(data, "message", min_length=1, max_length=10000),
        "model": optional_string(data, "model", default="abab6.5s-chat", max_length=100),
    }


def validate_ai_enhance_request() -> AIEnhanceRequest:
    data = parse_json_object()
    return {"requirements": require_string(data, "requirements", min_length=10, max_length=10000)}


def require_string(data, field, min_length=1, max_length=None):
    value = data.get(field)
    if value is None:
        raise ValidationError(f"'{field}' is required", code="missing_field", details={"field": field})
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be a string", code="invalid_field_type", details={"field": field})

    value = value.strip()
    if len(value) < min_length:
        raise ValidationError(
            f"'{field}' must be at least {min_length} characters",
            code="field_too_short",
            details={"field": field, "min_length": min_length},
        )
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"'{field}' must be at most {max_length} characters",
            code="field_too_long",
            details={"field": field, "max_length": max_length},
        )
    return value


def optional_string(data, field, default, allowed_values=None, max_length=None):
    value = data.get(field, default)
    if not isinstance(value, str):
        raise ValidationError(f"'{field}' must be a string", code="invalid_field_type", details={"field": field})

    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"'{field}' must be at most {max_length} characters",
            code="field_too_long",
            details={"field": field, "max_length": max_length},
        )
    if allowed_values and value not in allowed_values:
        raise ValidationError(
            f"'{field}' must be one of: {', '.join(sorted(allowed_values))}",
            code="invalid_field_value",
            details={"field": field, "allowed_values": sorted(allowed_values)},
        )
    return value


def optional_bool(data, field, default=False):
    value = data.get(field, default)
    if not isinstance(value, bool):
        raise ValidationError(f"'{field}' must be a boolean", code="invalid_field_type", details={"field": field})
    return value


def optional_int(data, field, default=None):
    value = data.get(field, default)
    if value is None or value == "":
        return default
    if not isinstance(value, int):
        raise ValidationError(f"'{field}' must be an integer", code="invalid_field_type", details={"field": field})
    return value
