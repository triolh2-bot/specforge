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
    model: str | None
    target_users: str | None
    business_goal: str | None
    success_metrics: str | None
    constraints: str | None
    integrations: str | None
    compliance: str | None
    monetization: str | None
    timeline: str | None
    budget: str | None
    scope_notes: str | None


class ProductBrief(TypedDict, total=False):
    problem: str
    target_users: list[str]
    business_goal: str
    success_metrics: list[str]
    constraints: list[str]
    integrations: list[str]
    compliance: list[str]
    monetization: str
    timeline: str
    budget: str
    scope_notes: str
    source_text: str
    answered_questions: list[dict[str, str]]


class ClarificationQuestion(TypedDict, total=False):
    id: str
    question: str
    why_it_matters: str
    blocking_section: str
    answer: str | None
    status: str


class GenerationStage(TypedDict, total=False):
    name: str
    status: str
    message: str


class GenerationRun(TypedDict, total=False):
    run_id: str
    status: str
    provider: str | None
    model: str | None
    stages: list[GenerationStage]
    quality_scores: dict[str, int]
    quality_score: int
    warnings: list[str]
    draft_version: int
    approved_version: int | None


class PRDDocument(TypedDict, total=False):
    overview: dict[str, Any]
    problem_statement: str
    personas: list[dict[str, Any]]
    goals: list[str]
    non_goals: list[str]
    assumptions: list[str]
    scope: dict[str, list[str]]
    prioritized_requirements: list[dict[str, Any]]
    user_journeys: list[dict[str, Any]]
    acceptance_criteria: list[dict[str, Any]]
    non_functional_requirements: dict[str, Any]
    dependencies: list[str]
    risks: list[dict[str, Any] | str]
    analytics: dict[str, Any]
    rollout: dict[str, Any]
    open_questions: list[dict[str, Any] | str]
    technical_recommendation: str | None


class AIChatRequest(TypedDict):
    model: str
    messages: list[dict[str, str]]
    temperature: float
    max_tokens: int


class AIEnhanceRequest(TypedDict):
    requirements: str
    domain: str
    missing_features: list[str]


class HealthCheck(TypedDict, total=False):
    name: str
    status: str
    message: str


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
