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


class HealthCheck(TypedDict, total=False):
    name: str
    status: str
    required: bool
    message: str
    details: dict[str, Any]


class HealthResponse(TypedDict, total=False):
    status: str
    version: str
    ready: bool
    endpoint: str
    mode: str
    summary: dict[str, str]
    checks: list[HealthCheck]
    request_id: str


class ProviderInfo(TypedDict, total=False):
    name: str
    display_name: str
    capabilities: list[str]
    configured: bool
    status: str
    models: list[str]


class ProviderListResponse(TypedDict, total=False):
    providers: list[ProviderInfo]
    available: list[str]
    preferred: str | None
