"""PRD (Product Requirements Document) generation service."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .ai_providers import (
    ChatMessage,
    ProviderResponse,
    ProviderStatus,
    registry,
)
from .domain_analysis import (
    calculate_rms,
    detect_conflicts,
    detect_domain,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
)
from .prompt_manager import (
    PRD_ENHANCEMENT_SCHEMA,
    PRD_REFINEMENT_SCHEMA,
    detect_prompt_injection,
    get_template,
    repair_output,
    render_prompt,
    sanitize_requirements,
    validate_output,
)

logger = logging.getLogger(__name__)


def generate_brief(
    project_name: str,
    project_type: str,
    core_idea: str,
    target_audience: str,
    key_features: str,
    ai_provider: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a plain-text project requirements brief using AI.

    Returns a dict with ``success``, ``brief`` (the generated text), and
    ``provider`` fields.
    """
    provider = registry.select(ai_provider)
    if provider is None:
        return {"success": False, "error": "No AI provider available. Please configure an API key."}

    template = get_template("brief_generation")
    if template is None:
        return {"success": False, "error": "Brief generation template not registered."}

    system_prompt, user_prompt = render_prompt(
        template,
        project_name=sanitize_requirements(project_name),
        project_type=project_type,
        core_idea=sanitize_requirements(core_idea),
        target_audience=target_audience,
        key_features=sanitize_requirements(key_features),
    )

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]

    try:
        result = provider.chat_completion(messages, temperature=0.8, max_tokens=1500)
    except Exception as exc:
        logger.error("Brief generation failed: %s", exc)
        return {"success": False, "error": str(exc)}

    if not result.success:
        return {"success": False, "error": result.error or "Provider returned an error."}

    # The brief is plain text — extract from data or raw_content
    data = result.data or {}
    brief_text = data.get("raw_content") or ""
    if not brief_text and isinstance(data, dict):
        # Some models wrap in JSON anyway
        brief_text = data.get("brief") or data.get("content") or str(data)

    if not brief_text:
        return {"success": False, "error": "AI returned an empty brief."}

    return {
        "success": True,
        "brief": brief_text.strip(),
        "provider": result.model or ai_provider or "unknown",
    }



def _call_provider(
    requirements: str,
    domain: str,
    missing_features: list[str],
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> ProviderResponse:
    """Select a provider, render the prompt template, and call the AI."""
    provider = registry.select(provider_name)
    if provider is None:
        logger.warning("No AI provider available for enhancement")
        return ProviderResponse(success=False, error="Provider unavailable")

    # Sanitize input to mitigate prompt injection
    cleaned_requirements = sanitize_requirements(requirements)
    injection_findings = detect_prompt_injection(cleaned_requirements)
    if injection_findings:
        logger.warning("Prompt injection detected: %s", injection_findings)
        # Continue with sanitized input but log the warning

    # Render the prompt template
    template = get_template("prd_enhancement")
    if template is None:
        logger.error("PRD enhancement template not registered")
        return ProviderResponse(success=False, error="Prompt template not available")

    missing_features_text = "\n".join(f"- {f}" for f in missing_features) if missing_features else "None detected"
    system_prompt, user_prompt = render_prompt(
        template,
        requirements=cleaned_requirements,
        domain=domain,
        missing_features=missing_features_text,
    )

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]

    selected_model = model  # None lets each provider use its own configured default

    try:
        result = provider.chat_completion(
            messages,
            model=selected_model,
            temperature=0.7,
            max_tokens=2000,
        )
    except Exception as exc:
        logger.error("Provider '%s' chat failed: %s", provider.name, exc)
        return ProviderResponse(success=False, error=str(exc), model=selected_model)

    # Validate the output against the schema
    if result.success and result.data:
        validation_errors = validate_output(result.data, PRD_ENHANCEMENT_SCHEMA)
        if validation_errors:
            logger.warning("AI output validation errors: %s", validation_errors)
            # Attempt automatic repair
            result.data = repair_output(result.data, PRD_ENHANCEMENT_SCHEMA)

    return result


def _call_refinement_provider(
    requirements: str,
    domain: str,
    answers: dict[str, str],
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> ProviderResponse:
    provider = registry.select(provider_name)
    if provider is None:
        logger.warning("No AI provider available for refinement")
        return ProviderResponse(success=False, error="Provider unavailable")

    cleaned_requirements = sanitize_requirements(requirements)
    qa_context = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])

    template = get_template("prd_refinement")
    if template is None:
        logger.error("PRD refinement template not registered")
        return ProviderResponse(success=False, error="Prompt template not available")

    system_prompt, user_prompt = render_prompt(
        template,
        requirements=cleaned_requirements,
        domain=domain,
        qa_context=qa_context,
    )

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]

    selected_model = model  # None lets each provider use its own configured default

    try:
        result = provider.chat_completion(
            messages,
            model=selected_model,
            temperature=0.7,
            max_tokens=2000,
        )
    except Exception as exc:
        logger.error("Provider '%s' chat failed: %s", provider.name, exc)
        return ProviderResponse(success=False, error=str(exc), model=selected_model)

    if result.success and result.data:
        validation_errors = validate_output(result.data, PRD_REFINEMENT_SCHEMA)
        if validation_errors:
            logger.warning("AI refinement output validation errors: %s", validation_errors)
            result.data = repair_output(result.data, PRD_REFINEMENT_SCHEMA)

    return result


def generate_refined_prd(
    original_requirements: str,
    domain: str,
    answers: dict[str, str],
    ai_provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    
    result = _call_refinement_provider(original_requirements, domain, answers, provider_name=ai_provider, model=model)
    
    ai_enhanced = None
    provider_result = None
    
    if result.success:
        provider_result = result.data
        ai_enhanced = {
            "status": "success",
            "provider": result.model or ai_provider or "minimax",
            "model": result.model,
            "data": provider_result,
            "usage": result.usage,
        }
    else:
        error_msg = result.error if result else "Provider unavailable"
        logger.info("AI refinement failed (%s)", error_msg)
        ai_enhanced = {
            "status": "failed",
            "provider": ai_provider or "minimax",
            "message": "AI refinement failed.",
            "error": error_msg,
        }

    return ai_enhanced


def _get_provider_info_for_response() -> dict[str, Any]:
    """Build the ai_providers block for the response payload."""
    providers_info: dict[str, Any] = {}
    for provider in registry.list_providers():
        providers_info[provider.name] = {
            "display_name": provider.display_name,
            "capabilities": [c.value for c in provider.capabilities],
            "status": provider.health_check().value,
            "configured": provider.is_configured(),
            "models": provider.get_available_models(),
        }
    return providers_info


def generate_prd(
    client_input: str,
    use_ai: bool = False,
    ai_provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a PRD from the given *client_input*.

    Parameters
    ----------
    client_input:
        Raw requirements text from the user.
    use_ai:
        Whether to attempt AI-based enhancement.
    ai_provider:
        Preferred provider name (e.g. ``"minimax"``).  Falls back automatically.
    model:
        Optional model identifier; defaults to provider / config default.
    """
    domain = detect_domain(client_input)
    missing_features = detect_missing_features(domain, client_input)
    questions = generate_questions(domain, client_input, missing_features)
    implied_users = detect_implied_users(client_input)
    conflicts = detect_conflicts(client_input)
    rms = calculate_rms(client_input, domain)

    ai_enhanced: Optional[dict[str, Any]] = None
    provider_result: Optional[dict[str, Any]] = None

    if use_ai:
        result = _call_provider(client_input, domain, missing_features, provider_name=ai_provider, model=model)

        if result is not None and result.success:
            provider_result = result.data
            ai_enhanced = {
                "status": "success",
                "provider": result.model or ai_provider or "minimax",
                "model": result.model,
                "data": provider_result,
                "usage": result.usage,
            }
            if provider_result.get("clarification_questions"):
                questions = provider_result["clarification_questions"][:5]
        else:
            error_msg = result.error if result else "Provider unavailable"
            logger.info("AI enhancement failed (%s), using rule-based fallback", error_msg)
            ai_enhanced = {
                "status": "fallback",
                "provider": ai_provider or "minimax",
                "message": "Using rule-based analysis (AI enhancement unavailable)",
                "error": error_msg,
            }

    # -- Build PRD (rule-based defaults) ------------------------------------
    prd_summary = client_input[:300]
    tech_stack: Optional[str] = None
    risks = [
        "Scope creep from unclear requirements",
        "Third-party API integration challenges",
        "Timeline delays from dependencies",
    ]
    timeline = "To be determined"

    if provider_result:
        prd_summary = provider_result.get("prd_summary", prd_summary)
        tech_stack = provider_result.get("tech_stack_recommendation")
        if provider_result.get("risk_factors"):
            risks = provider_result["risk_factors"][:3]
        timeline = provider_result.get("estimated_timeline", timeline)

    return {
        "success": True,
        "domain": domain,
        "implied_users": implied_users,
        "missing_features": missing_features,
        "clarification_questions": questions,
        "conflicts": conflicts,
        "rms": rms,
        "prd": {
            "title": "Project Specification Document",
            "version": "1.0",
            "overview": {
                "summary": prd_summary,
                "project_type": domain,
                "target_users": implied_users,
            },
            "scope": {
                "in_scope": [
                    f"Core {domain} functionality",
                    "User authentication and management",
                    "Admin dashboard with analytics",
                    "Basic reporting",
                ],
                "out_of_scope": [
                    "Advanced AI/ML features",
                    "Custom integrations",
                    "Mobile native apps (MVP phase)",
                ],
            },
            "functional_requirements": generate_functional_reqs(domain, client_input),
            "non_functional": {
                "performance": "Page load under 3 seconds",
                "security": "HTTPS, secure authentication, data encryption",
                "scalability": "Support 1000+ concurrent users initially",
                "reliability": "99.9% uptime target",
            },
            "technical_constraints": {
                "timeline": timeline,
                "budget": "To be determined",
                "team_size": "1-3 developers recommended",
                "tech_stack": tech_stack,
            },
            "risks": risks,
            "next_steps": [
                "Answer clarification questions",
                "Finalize scope with stakeholders",
                "Create technical specification",
            ],
        },
        "ai_enhanced": ai_enhanced,
        "ai_providers": _get_provider_info_for_response(),
    }
