from flask import request

from .contracts import AnalyzeRequest, MiniMaxChatRequest, MiniMaxEnhanceRequest


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
    return {
        "requirements": require_string(data, "requirements", min_length=10, max_length=10000),
        "ai_enhance": optional_bool(data, "ai_enhance", default=False),
        "ai_provider": optional_string(data, "ai_provider", default="minimax", allowed_values={"minimax", "openrouter"}),
    }


def validate_refine_request() -> dict:
    data = parse_json_object()
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValidationError("'answers' must be a JSON object", code="invalid_field_type", details={"field": "answers"})
    
    # Filter empty answers
    valid_answers = {k: v for k, v in answers.items() if isinstance(v, str) and v.strip()}
    if not valid_answers:
        raise ValidationError("At least one answer must be provided", code="missing_answers")

    return {
        "analysis_id": require_string(data, "analysis_id", min_length=36, max_length=36),
        "answers": valid_answers,
        "ai_provider": optional_string(data, "ai_provider", default="minimax", allowed_values={"minimax", "openrouter"}),
    }


def validate_minimax_chat_request() -> MiniMaxChatRequest:
    data = parse_json_object()
    return {
        "message": require_string(data, "message", min_length=1, max_length=10000),
        "model": optional_string(data, "model", default="abab6.5s-chat", max_length=100),
    }


def validate_minimax_enhance_request() -> MiniMaxEnhanceRequest:
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
