from typing import Any, TypedDict


class ErrorBody(TypedDict, total=False):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(TypedDict, total=False):
    success: bool
    error: ErrorBody
    request_id: str


class AnalyzeRequest(TypedDict):
    requirements: str
    ai_enhance: bool
    ai_provider: str


class MiniMaxChatRequest(TypedDict):
    message: str
    model: str


class MiniMaxEnhanceRequest(TypedDict):
    requirements: str


class HealthResponse(TypedDict, total=False):
    status: str
    version: str
    features: list[str]
    ai_providers: dict[str, Any]
    request_id: str
