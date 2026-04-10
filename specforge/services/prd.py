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
    detect_prompt_injection,
    get_template,
    repair_output,
    render_prompt,
    sanitize_requirements,
    validate_output,
)

logger = logging.getLogger(__name__)


def _build_enhance_prompt(
    requirements: str,
    domain: str,
    missing_features: list[str],
) -> str:
    missing_features_text = "\n".join(f"- {feature}" for feature in missing_features) if missing_features else "None detected"

    return (
        f"Analyze the following software requirements and provide a structured enhancement analysis.\n\n"
        f"REQUIREMENTS:\n{requirements}\n\n"
        f"DETECTED DOMAIN: {domain}\n\n"
        f"MISSING FEATURES DETECTED:\n{missing_features_text}\n\n"
        f'Please provide a structured JSON response with the following fields:\n\n'
        f'1. "prd_summary": A comprehensive 2-3 paragraph summary of the project that would serve as a PRD overview. '
        f"Include the purpose, target users, and key value propositions.\n\n"
        f'2. "clarification_questions": An array of exactly 5 smart, specific clarification questions '
        f"tailored to these requirements. Questions should be actionable and help scope the project better.\n\n"
        f'3. "tech_stack_recommendation": A recommended technology stack for the {domain} domain, '
        f"including frontend, backend, database, and any specific frameworks/libraries.\n\n"
        f'4. "risk_factors": An array of exactly 3 specific risk factors relevant to this particular project '
        f"based on the requirements and domain.\n\n"
        f'5. "estimated_timeline": A realistic development timeline estimate (e.g., "8-12 weeks", "3-4 months") '
        f"with brief justification.\n\n"
        f"Return ONLY valid JSON in this exact format:\n"
        f"{{\n"
        f'  "prd_summary": "string",\n'
        f'  "clarification_questions": ["q1", "q2", "q3", "q4", "q5"],\n'
        f'  "tech_stack_recommendation": "string",\n'
        f'  "risk_factors": ["risk1", "risk2", "risk3"],\n'
        f'  "estimated_timeline": "string"\n'
        f"}}"
    )


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

    selected_model = model or "MiniMax-M2.5"

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
