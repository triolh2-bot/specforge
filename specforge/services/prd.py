"""Canonical PRD generation pipeline and legacy response projection."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional
from uuid import uuid4

from .ai_providers import ChatMessage, ProviderResponse, registry
from .domain_analysis import (
    calculate_rms,
    detect_conflicts,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
)
from .domain_intelligence import detect_domain_detailed
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


def _split_values(value: Optional[str]) -> list[str]:
    if not value:
        return []
    normalized = value.replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _question_id(question: str, blocking_section: str) -> str:
    key = f"{blocking_section}:{question}".encode("utf-8")
    return hashlib.sha1(key, usedforsecurity=False).hexdigest()[:12]


def _stage(name: str, status: str, message: str) -> dict[str, str]:
    return {"name": name, "status": status, "message": message}


def generate_brief(
    project_name: str,
    project_type: str,
    core_idea: str,
    target_audience: str,
    key_features: str,
    ai_provider: Optional[str] = None,
) -> dict[str, Any]:
    provider = registry.select(ai_provider)
    if provider is None:
        return {"success": False, "error": "No AI provider available. Please configure an API key."}

    template = get_template("brief_generation")
    if template is None:
        logger.error("Brief generation template not registered")
        return {"success": False, "error": "Brief generation template not registered."}

    try:
        system_prompt, user_prompt = render_prompt(
            template,
            project_name=sanitize_requirements(project_name),
            project_type=project_type,
            core_idea=sanitize_requirements(core_idea),
            target_audience=target_audience,
            key_features=sanitize_requirements(key_features),
        )
    except KeyError as exc:
        logger.error("Brief generation template missing required variable: %s", exc)
        return {"success": False, "error": f"Template error: missing {exc}"}
    except Exception as exc:
        logger.error("Failed to render brief template: %s", exc)
        return {"success": False, "error": f"Template rendering failed: {exc}"}

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

    data = result.data or {}
    brief_text = data.get("raw_content") or data.get("brief") or data.get("content") or ""
    if not brief_text:
        return {"success": False, "error": "AI returned an empty brief."}

    return {
        "success": True,
        "brief": brief_text.strip(),
        "provider": result.model or ai_provider or "unknown",
    }


def _recover_provider_output(result: ProviderResponse, schema: dict[str, Any]) -> tuple[ProviderResponse, list[str]]:
    warnings: list[str] = []
    if not result.success or not result.data:
        return result, warnings

    validation_errors = validate_output(result.data, schema)
    if not validation_errors:
        return result, warnings

    warnings.append("AI output failed strict validation; attempting repair.")
    repaired = repair_output(result.data, schema)
    repaired_errors = validate_output(repaired, schema)
    if repaired_errors:
        result.success = False
        result.error = "AI output remained invalid after repair"
        warnings.extend(repaired_errors)
        return result, warnings

    result.data = repaired
    warnings.append("AI output repaired successfully.")
    return result, warnings


def _call_provider(
    requirements: str,
    domain: str,
    missing_features: list[str],
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> tuple[ProviderResponse, list[str]]:
    provider = registry.select(provider_name)
    if provider is None:
        logger.warning("No AI provider available for enhancement")
        return ProviderResponse(success=False, error="Provider unavailable"), []

    template = get_template("prd_enhancement")
    if template is None:
        logger.error("PRD enhancement template not registered")
        return ProviderResponse(success=False, error="Prompt template not available"), []

    cleaned_requirements = sanitize_requirements(requirements)
    missing_features_text = "\n".join(f"- {feature}" for feature in missing_features) if missing_features else "None detected"
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

    try:
        result = provider.chat_completion(messages, model=model, temperature=0.7, max_tokens=2000)
    except Exception as exc:
        logger.error("Provider '%s' chat failed: %s", provider.name, exc)
        return ProviderResponse(success=False, error=str(exc), model=model), []

    return _recover_provider_output(result, PRD_ENHANCEMENT_SCHEMA)


def _call_refinement_provider(
    requirements: str,
    domain: str,
    answers: dict[str, str],
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> tuple[ProviderResponse, list[str]]:
    provider = registry.select(provider_name)
    if provider is None:
        logger.warning("No AI provider available for refinement")
        return ProviderResponse(success=False, error="Provider unavailable"), []

    template = get_template("prd_refinement")
    if template is None:
        logger.error("PRD refinement template not registered")
        return ProviderResponse(success=False, error="Prompt template not available"), []

    cleaned_requirements = sanitize_requirements(requirements)
    qa_context = "\n\n".join([f"Q: {question}\nA: {answer}" for question, answer in answers.items()])
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

    try:
        result = provider.chat_completion(messages, model=model, temperature=0.7, max_tokens=2000)
    except Exception as exc:
        logger.error("Provider '%s' refinement failed: %s", provider.name, exc)
        return ProviderResponse(success=False, error=str(exc), model=model), []

    return _recover_provider_output(result, PRD_REFINEMENT_SCHEMA)


def _normalize_input_to_brief(
    client_input: str,
    intake_fields: Optional[dict[str, Any]] = None,
    answers: Optional[dict[str, str]] = None,
    previous_brief: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], list[str]]:
    intake_fields = intake_fields or {}
    previous_brief = previous_brief or {}
    answers = answers or {}
    warnings: list[str] = []
    source_text = sanitize_requirements(client_input or previous_brief.get("source_text", ""))

    target_users = _split_values(intake_fields.get("target_users")) or list(previous_brief.get("target_users", []))
    success_metrics = _split_values(intake_fields.get("success_metrics")) or list(previous_brief.get("success_metrics", []))
    constraints = _split_values(intake_fields.get("constraints")) or list(previous_brief.get("constraints", []))
    integrations = _split_values(intake_fields.get("integrations")) or list(previous_brief.get("integrations", []))
    compliance = _split_values(intake_fields.get("compliance")) or list(previous_brief.get("compliance", []))

    if not target_users:
        target_users = detect_implied_users(source_text)
        warnings.append("Target users were inferred from the brief.")
    if not intake_fields.get("business_goal") and not previous_brief.get("business_goal"):
        warnings.append("Business goal is missing from the intake.")
    if not success_metrics:
        warnings.append("Success metrics are missing from the intake.")
    if not constraints:
        warnings.append("Constraints are missing from the intake.")
    if not intake_fields.get("monetization") and not previous_brief.get("monetization"):
        warnings.append("Monetization model is unresolved.")

    answered_questions = [
        {"question": question, "answer": answer}
        for question, answer in answers.items()
        if isinstance(question, str) and isinstance(answer, str) and answer.strip()
    ]

    brief = {
        "problem": source_text or intake_fields.get("scope_notes") or previous_brief.get("problem") or "Product idea requires clarification.",
        "target_users": target_users,
        "business_goal": intake_fields.get("business_goal") or previous_brief.get("business_goal") or "Define the core business outcome for this product.",
        "success_metrics": success_metrics,
        "constraints": constraints,
        "integrations": integrations,
        "compliance": compliance,
        "monetization": intake_fields.get("monetization") or previous_brief.get("monetization") or "To be determined",
        "timeline": intake_fields.get("timeline") or previous_brief.get("timeline") or "To be determined",
        "budget": intake_fields.get("budget") or previous_brief.get("budget") or "To be determined",
        "scope_notes": intake_fields.get("scope_notes") or previous_brief.get("scope_notes") or "",
        "source_text": source_text,
        "answered_questions": answered_questions,
    }
    return brief, warnings


def _classify_domain_and_scope(brief: dict[str, Any]) -> dict[str, Any]:
    classification_input = "\n".join(
        [
            brief.get("source_text", ""),
            brief.get("business_goal", ""),
            ", ".join(brief.get("integrations", [])),
            ", ".join(brief.get("constraints", [])),
            "\n".join(f"{item['question']} {item['answer']}" for item in brief.get("answered_questions", [])),
        ]
    )
    detailed = detect_domain_detailed(classification_input)
    ranked_scores = sorted(detailed.all_scores.items(), key=lambda item: item[1], reverse=True)
    primary_domain = detailed.primary_domain
    secondary_domains = [name for name, score in ranked_scores[1:3] if score > 0]
    top_score = ranked_scores[0][1] if ranked_scores else 0
    second_score = ranked_scores[1][1] if len(ranked_scores) > 1 else 0
    mixed_scope = bool(top_score and second_score and second_score >= top_score * 0.6)
    return {
        "primary_domain": primary_domain,
        "secondary_domains": secondary_domains,
        "confidence": detailed.confidence,
        "matched_signals": detailed.matched_rules.get(primary_domain, []),
        "mixed_scope": mixed_scope,
        "all_scores": detailed.all_scores,
    }


def _guess_blocking_section(question: str) -> str:
    lower = question.lower()
    if any(term in lower for term in ("metric", "success", "kpi")):
        return "analytics"
    if any(term in lower for term in ("budget", "pricing", "monetization", "billing")):
        return "business_model"
    if any(term in lower for term in ("timeline", "launch", "deadline")):
        return "rollout"
    if any(term in lower for term in ("auth", "security", "compliance", "sso")):
        return "non_functional_requirements"
    if any(term in lower for term in ("integrat", "provider", "api", "webhook")):
        return "dependencies"
    return "scope"


def _build_question(
    question: str,
    why_it_matters: str,
    blocking_section: str,
    answers_by_id: dict[str, str],
    answers_by_text: dict[str, str],
) -> dict[str, Any]:
    question_id = _question_id(question, blocking_section)
    answer = answers_by_id.get(question_id) or answers_by_text.get(question)
    return {
        "id": question_id,
        "question": question,
        "why_it_matters": why_it_matters,
        "blocking_section": blocking_section,
        "answer": answer,
        "status": "answered" if answer else "open",
    }


def _generate_clarification_questions_v2(
    brief: dict[str, Any],
    domain_context: dict[str, Any],
    missing_features: list[str],
    answers_by_id: Optional[dict[str, str]] = None,
    answers_by_text: Optional[dict[str, str]] = None,
    provider_questions: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    answers_by_id = answers_by_id or {}
    answers_by_text = answers_by_text or {}
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(question: str, why: str, section: str):
        if question in seen:
            return
        seen.add(question)
        questions.append(_build_question(question, why, section, answers_by_id, answers_by_text))

    if brief.get("business_goal", "").startswith("Define the core business outcome"):
        add(
            "What concrete business outcome should this product drive in its first release?",
            "The PRD cannot prioritize features correctly without a business goal.",
            "goals",
        )
    if brief.get("monetization") == "To be determined":
        add(
            "How will this product make money or justify its investment?",
            "Monetization affects scope, analytics, and roadmap decisions.",
            "business_model",
        )
    if brief.get("timeline") == "To be determined":
        add(
            "What launch timeline or deadline should the plan optimize for?",
            "Timeline directly changes scope, rollout, and delivery risk.",
            "rollout",
        )
    if brief.get("budget") == "To be determined":
        add(
            "What budget range or resource ceiling should the PRD assume?",
            "Budget constraints change scope, team assumptions, and technology choices.",
            "constraints",
        )
    if not brief.get("success_metrics"):
        add(
            "Which measurable success metrics should define whether this release worked?",
            "Without success metrics the document cannot validate product value.",
            "analytics",
        )
    if domain_context.get("mixed_scope"):
        add(
            "Is this product primarily one domain with supporting features, or a true multi-domain platform?",
            "Mixed domain scope changes architecture, roadmap, and MVP boundaries.",
            "scope",
        )

    for question in provider_questions or []:
        add(question, "This unanswered decision materially affects the generated PRD.", _guess_blocking_section(question))

    for question in generate_questions(domain_context["primary_domain"], brief.get("source_text", ""), missing_features):
        add(question, "This domain-specific decision affects implementation and planning quality.", _guess_blocking_section(question))

    return questions[:7]


def _build_summary(brief: dict[str, Any], domain_context: dict[str, Any], provider_result: Optional[dict[str, Any]]) -> str:
    if provider_result and provider_result.get("prd_summary"):
        return provider_result["prd_summary"]

    users = ", ".join(brief.get("target_users", [])) or "target users"
    summary = (
        f"This {domain_context['primary_domain']} product is intended to solve: {brief.get('problem', 'Unspecified problem statement')}. "
        f"It is aimed at {users} and is expected to support the business goal of {brief.get('business_goal', 'an outcome still to be clarified')}."
    )
    if brief.get("scope_notes"):
        summary += f" Scope notes: {brief['scope_notes']}."
    if brief.get("monetization") and brief["monetization"] != "To be determined":
        summary += f" Monetization model: {brief['monetization']}."
    if brief.get("answered_questions"):
        summary += " Clarifications have been incorporated into this draft."
    return summary


def _build_prioritized_requirements(domain: str, brief: dict[str, Any], missing_features: list[str]) -> list[dict[str, Any]]:
    base_requirements = generate_functional_reqs(domain, brief.get("source_text", ""))
    prioritized: list[dict[str, Any]] = []
    for idx, requirement in enumerate(base_requirements[:10], start=1):
        priority = "must" if idx <= 4 else "should" if idx <= 7 else "could"
        prioritized.append(
            {
                "id": f"REQ-{idx:02d}",
                "name": requirement,
                "priority": priority,
                "rationale": "Derived from the normalized product brief and domain profile.",
            }
        )
    for feature in missing_features[:3]:
        prioritized.append(
            {
                "id": f"GAP-{len(prioritized) + 1:02d}",
                "name": feature,
                "priority": "should",
                "rationale": "Common production requirement missing from the intake and worth resolving before build.",
            }
        )
    return prioritized


def _build_acceptance_criteria(prioritized_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = []
    for item in prioritized_requirements[:6]:
        criteria.append(
            {
                "requirement_id": item["id"],
                "criteria": [
                    f"{item['name']} is implemented in the primary user workflow.",
                    f"{item['name']} includes success, failure, and audit handling where applicable.",
                ],
            }
        )
    return criteria


def _build_prd_document(
    brief: dict[str, Any],
    domain_context: dict[str, Any],
    missing_features: list[str],
    questions_v2: list[dict[str, Any]],
    provider_result: Optional[dict[str, Any]],
) -> dict[str, Any]:
    prioritized_requirements = _build_prioritized_requirements(domain_context["primary_domain"], brief, missing_features)
    acceptance_criteria = _build_acceptance_criteria(prioritized_requirements)
    unanswered = [question for question in questions_v2 if question["status"] != "answered"]

    personas = [
        {
            "name": user,
            "needs": [
                f"{user} can complete their primary workflow without ambiguity.",
                f"{user} receives the controls and visibility needed for the release scope.",
            ],
        }
        for user in brief.get("target_users", [])
    ]

    return {
        "overview": {
            "title": "Project Specification Document",
            "summary": _build_summary(brief, domain_context, provider_result),
            "domain": domain_context["primary_domain"],
            "confidence": domain_context["confidence"],
            "secondary_domains": domain_context["secondary_domains"],
        },
        "problem_statement": brief.get("problem", "Product problem statement is missing."),
        "personas": personas,
        "goals": [brief.get("business_goal")] if brief.get("business_goal") else [],
        "non_goals": [
            "Unbounded custom integrations unless explicitly prioritized.",
            "Premature enterprise-grade expansion before core workflows are validated.",
        ],
        "assumptions": [
            f"Timeline assumption: {brief.get('timeline', 'To be determined')}",
            f"Budget assumption: {brief.get('budget', 'To be determined')}",
            f"Monetization assumption: {brief.get('monetization', 'To be determined')}",
        ],
        "scope": {
            "in_scope": [item["name"] for item in prioritized_requirements if item["priority"] in {"must", "should"}][:8],
            "out_of_scope": [
                "Large custom enterprise integrations unless separately approved.",
                "Adjacent platform bets that are not essential to the first release.",
            ],
        },
        "prioritized_requirements": prioritized_requirements,
        "user_journeys": [
            {
                "name": f"{persona['name']} core journey",
                "steps": [
                    "Discovers the product entry point",
                    "Completes the primary product workflow",
                    "Receives confirmation, results, or next-step guidance",
                ],
            }
            for persona in personas[:3]
        ],
        "acceptance_criteria": acceptance_criteria,
        "non_functional_requirements": {
            "performance": "Critical workflows should respond within 3 seconds under target load.",
            "security": "Use secure authentication, least-privilege access, encrypted transport, and protected secrets.",
            "scalability": "Support initial production usage with a clear path to horizontal scaling.",
            "reliability": "Core workflows should target 99.9% availability with monitored failure handling.",
            "compliance": brief.get("compliance", []),
            "constraints": brief.get("constraints", []),
        },
        "dependencies": brief.get("integrations", []),
        "risks": provider_result.get("risk_factors", []) if provider_result and provider_result.get("risk_factors") else [
            "Scope creep from unresolved intake gaps.",
            "Delivery risk from unclear integrations or compliance requirements.",
            "Product quality risk if acceptance criteria remain too thin.",
        ],
        "analytics": {
            "success_metrics": brief.get("success_metrics", []),
            "tracking_requirements": [
                "Track adoption of the primary workflow.",
                "Track conversion or completion for the main success event.",
                "Track operational failures for core user actions.",
            ],
        },
        "rollout": {
            "timeline": provider_result.get("estimated_timeline") if provider_result and provider_result.get("estimated_timeline") else brief.get("timeline", "To be determined"),
            "phases": [
                "Intake completion and scope lock",
                "MVP implementation",
                "Release readiness and launch",
            ],
        },
        "open_questions": unanswered,
        "technical_recommendation": provider_result.get("tech_stack_recommendation") if provider_result else None,
    }


def _project_legacy_response(
    brief: dict[str, Any],
    prd_document: dict[str, Any],
    domain_context: dict[str, Any],
    missing_features: list[str],
    questions_v2: list[dict[str, Any]],
    conflicts: list[str],
    draft_version: int,
) -> dict[str, Any]:
    risks = prd_document.get("risks", [])
    normalized_risks = [risk["summary"] if isinstance(risk, dict) and "summary" in risk else str(risk) for risk in risks]
    legacy_prd = {
        "title": prd_document.get("overview", {}).get("title", "Project Specification Document"),
        "version": f"2.{max(draft_version - 1, 0)}",
        "overview": {
            "summary": prd_document.get("overview", {}).get("summary", ""),
            "project_type": domain_context["primary_domain"],
            "target_users": brief.get("target_users", []),
        },
        "scope": prd_document.get("scope", {}),
        "functional_requirements": [item["name"] for item in prd_document.get("prioritized_requirements", [])],
        "non_functional": {
            "performance": prd_document.get("non_functional_requirements", {}).get("performance", ""),
            "security": prd_document.get("non_functional_requirements", {}).get("security", ""),
            "scalability": prd_document.get("non_functional_requirements", {}).get("scalability", ""),
            "reliability": prd_document.get("non_functional_requirements", {}).get("reliability", ""),
        },
        "technical_constraints": {
            "timeline": prd_document.get("rollout", {}).get("timeline", "To be determined"),
            "budget": brief.get("budget", "To be determined"),
            "team_size": "1-3 developers recommended",
            "tech_stack": prd_document.get("technical_recommendation"),
        },
        "risks": normalized_risks[:3],
        "next_steps": [
            "Resolve all open clarification questions.",
            "Approve the latest draft before export or sharing.",
            "Translate approved scope into a delivery plan.",
        ],
    }
    return {
        "domain": domain_context["primary_domain"],
        "implied_users": brief.get("target_users", []),
        "missing_features": missing_features,
        "clarification_questions": [item["question"] for item in questions_v2],
        "conflicts": conflicts,
        "rms": calculate_rms(brief.get("source_text", ""), domain_context["primary_domain"]),
        "prd": legacy_prd,
    }


def _score_quality(
    brief: dict[str, Any],
    prd_document: dict[str, Any],
    questions_v2: list[dict[str, Any]],
    conflicts: list[str],
) -> tuple[dict[str, int], list[str]]:
    warnings: list[str] = []
    completeness = 55
    if brief.get("business_goal") and not brief["business_goal"].startswith("Define the core business outcome"):
        completeness += 10
    if brief.get("success_metrics"):
        completeness += 10
    if brief.get("constraints"):
        completeness += 10
    if not questions_v2:
        completeness += 10

    consistency = 85 - min(25, len(conflicts) * 10)
    business_coverage = 50
    if brief.get("monetization") and brief["monetization"] != "To be determined":
        business_coverage += 20
    else:
        warnings.append("Monetization remains unresolved.")
    if brief.get("budget") != "To be determined":
        business_coverage += 10
    else:
        warnings.append("Budget remains unresolved.")
    if brief.get("timeline") != "To be determined":
        business_coverage += 10
    else:
        warnings.append("Timeline remains unresolved.")

    clarity = 70
    if prd_document.get("acceptance_criteria"):
        clarity += 10
    if len(prd_document.get("open_questions", [])) > 3:
        clarity -= 10
        warnings.append("Too many open questions remain for a production-ready PRD.")
    if not prd_document.get("acceptance_criteria"):
        warnings.append("Acceptance criteria are missing or too thin.")
    if not brief.get("constraints"):
        warnings.append("Constraints are missing from the intake.")

    return {
        "completeness": max(0, min(100, completeness)),
        "consistency": max(0, min(100, consistency)),
        "business_coverage": max(0, min(100, business_coverage)),
        "clarity": max(0, min(100, clarity)),
    }, warnings


def _compute_section_diffs(previous_document: Optional[dict[str, Any]], current_document: dict[str, Any]) -> list[dict[str, Any]]:
    if not previous_document:
        return [{"section": section, "change_type": "added"} for section in current_document.keys()]

    diffs: list[dict[str, Any]] = []
    for section, value in current_document.items():
        if previous_document.get(section) != value:
            diffs.append({"section": section, "change_type": "updated"})
    for section in previous_document.keys():
        if section not in current_document:
            diffs.append({"section": section, "change_type": "removed"})
    return diffs


def _get_provider_info_for_response() -> dict[str, Any]:
    providers_info: dict[str, Any] = {}
    for provider in registry.list_providers():
        providers_info[provider.name] = {
            "display_name": provider.display_name,
            "capabilities": [capability.value for capability in provider.capabilities],
            "status": provider.health_check().value,
            "configured": provider.is_configured(),
            "models": list(provider.get_available_models()),
        }
    return providers_info


def _validate_prd_document(prd_document: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    required_sections = [
        "overview",
        "problem_statement",
        "personas",
        "goals",
        "scope",
        "prioritized_requirements",
        "acceptance_criteria",
        "non_functional_requirements",
        "analytics",
        "rollout",
    ]
    for section in required_sections:
        value = prd_document.get(section)
        if value in (None, "", [], {}):
            findings.append(f"Section '{section}' is missing or empty.")
    if not prd_document.get("analytics", {}).get("success_metrics"):
        findings.append("Success metrics are missing from the analytics section.")
    if not prd_document.get("personas"):
        findings.append("No personas were generated.")
    return findings


def _build_ai_status(
    use_ai: bool,
    provider_name: Optional[str],
    provider_result: Optional[ProviderResponse],
    provider_data: Optional[dict[str, Any]],
    warnings: list[str],
) -> Optional[dict[str, Any]]:
    if not use_ai:
        return None
    if provider_result and provider_result.success:
        return {
            "status": "success",
            "provider": provider_name,
            "model": provider_result.model,
            "data": provider_data or {},
            "warnings": warnings,
        }
    return {
        "status": "fallback",
        "provider": provider_name,
        "model": provider_result.model if provider_result else None,
        "error": provider_result.error if provider_result else "Provider unavailable",
        "warnings": warnings,
    }


def _build_generation_run(
    run_id: str,
    stages: list[dict[str, str]],
    quality_scores: dict[str, int],
    warnings: list[str],
    provider_name: Optional[str],
    model: Optional[str],
    draft_version: int,
    approved_version: Optional[int],
) -> dict[str, Any]:
    average_quality = round(sum(quality_scores.values()) / max(len(quality_scores), 1))
    return {
        "run_id": run_id,
        "status": "completed",
        "provider": provider_name,
        "model": model,
        "stages": stages,
        "quality_scores": quality_scores,
        "quality_score": average_quality,
        "warnings": warnings,
        "draft_version": draft_version,
        "approved_version": approved_version,
    }


def generate_prd(
    requirements: str,
    use_ai: bool = False,
    ai_provider: Optional[str] = None,
    model: Optional[str] = None,
    intake_fields: Optional[dict[str, Any]] = None,
    previous_document: Optional[dict[str, Any]] = None,
    previous_brief: Optional[dict[str, Any]] = None,
    previous_version: Optional[int] = None,
    approved_version: Optional[int] = None,
    answers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    run_id = str(uuid4())
    effective_provider = ai_provider
    if use_ai and not effective_provider:
        selected_provider = registry.select()
        effective_provider = selected_provider.name if selected_provider else None
    stages = [_stage("input_normalization", "running", "Normalizing product brief input.")]
    warnings: list[str] = []

    injection_findings = detect_prompt_injection(requirements or "")
    if injection_findings:
        warnings.extend(injection_findings)

    brief, normalization_warnings = _normalize_input_to_brief(
        requirements,
        intake_fields=intake_fields,
        answers=answers,
        previous_brief=previous_brief,
    )
    warnings.extend(normalization_warnings)
    stages[-1] = _stage("input_normalization", "completed", "Structured product brief created.")

    stages.append(_stage("domain_classification", "running", "Detecting primary domain and scope."))
    domain_context = _classify_domain_and_scope(brief)
    stages[-1] = _stage(
        "domain_classification",
        "completed",
        f"Detected domain '{domain_context['primary_domain']}' with {domain_context['confidence']} confidence.",
    )

    stages.append(_stage("gap_detection", "running", "Detecting missing details and clarification gaps."))
    missing_features = detect_missing_features(domain_context["primary_domain"], requirements or brief.get("problem", ""))
    conflicts = detect_conflicts(requirements or brief.get("problem", ""))
    answers_by_text = dict(answers or {})
    answers_by_id: dict[str, str] = {}
    provider_result: Optional[ProviderResponse] = None
    provider_payload: Optional[dict[str, Any]] = None
    ai_warnings: list[str] = []

    if use_ai:
        stages.append(_stage("prd_synthesis", "running", "Generating structured AI guidance for PRD synthesis."))
        if answers:
            provider_result, ai_warnings = _call_refinement_provider(
                requirements=brief.get("source_text", ""),
                domain=domain_context["primary_domain"],
                answers=answers,
                provider_name=effective_provider,
                model=model,
            )
        else:
            provider_result, ai_warnings = _call_provider(
                requirements=brief.get("source_text", ""),
                domain=domain_context["primary_domain"],
                missing_features=missing_features,
                provider_name=effective_provider,
                model=model,
            )
        warnings.extend(ai_warnings)
        if provider_result and provider_result.success:
            provider_payload = provider_result.data or {}
            stages[-1] = _stage("prd_synthesis", "completed", "AI synthesis completed and validated.")
        else:
            stages[-1] = _stage("prd_synthesis", "completed", "AI synthesis unavailable; using deterministic fallback.")
    else:
        stages.append(_stage("prd_synthesis", "skipped", "AI synthesis not requested."))

    provider_questions = provider_payload.get("clarification_questions", []) if provider_payload else []
    questions_v2 = _generate_clarification_questions_v2(
        brief,
        domain_context,
        missing_features,
        answers_by_id=answers_by_id,
        answers_by_text=answers_by_text,
        provider_questions=provider_questions,
    )
    stages[2] = _stage("gap_detection", "completed", f"Generated {len(questions_v2)} clarification questions.")

    prd_document = _build_prd_document(
        brief=brief,
        domain_context=domain_context,
        missing_features=missing_features,
        questions_v2=questions_v2,
        provider_result=provider_payload,
    )

    stages.append(_stage("quality_validation", "running", "Validating completeness and consistency."))
    quality_scores, quality_warnings = _score_quality(brief, prd_document, questions_v2, conflicts)
    warnings.extend(quality_warnings)
    warnings.extend(_validate_prd_document(prd_document))
    stages[-1] = _stage("quality_validation", "completed", "Quality validation completed.")

    draft_version = (previous_version or 0) + 1
    section_diffs = _compute_section_diffs(previous_document, prd_document)
    generation_run = _build_generation_run(
        run_id=run_id,
        stages=stages,
        quality_scores=quality_scores,
        warnings=warnings,
        provider_name=effective_provider if use_ai else None,
        model=(provider_result.model if provider_result else model),
        draft_version=draft_version,
        approved_version=approved_version,
    )
    legacy_response = _project_legacy_response(
        brief=brief,
        prd_document=prd_document,
        domain_context=domain_context,
        missing_features=missing_features,
        questions_v2=questions_v2,
        conflicts=conflicts,
        draft_version=draft_version,
    )
    ai_status = _build_ai_status(use_ai, effective_provider, provider_result, provider_payload, ai_warnings)
    legacy_questions = provider_questions[:5] if provider_questions else legacy_response["clarification_questions"]

    return {
        "success": True,
        "domain": legacy_response["domain"],
        "implied_users": legacy_response["implied_users"],
        "missing_features": legacy_response["missing_features"],
        "clarification_questions": legacy_questions,
        "clarification_questions_v2": questions_v2,
        "conflicts": conflicts,
        "rms": legacy_response["rms"],
        "prd": legacy_response["prd"],
        "prd_document": prd_document,
        "product_brief": brief,
        "generation_run": generation_run,
        "section_diffs": section_diffs,
        "draft_version": draft_version,
        "approved_version": approved_version,
        "approval_state": "draft",
        "answers": answers or {},
        "ai_enhanced": ai_status,
        "ai_providers": _get_provider_info_for_response(),
    }


def generate_refined_prd(
    analysis: dict[str, Any],
    answers: dict[str, str],
    ai_provider: Optional[str] = None,
    model: Optional[str] = None,
    version_number: Optional[int] = None,
) -> dict[str, Any]:
    previous_version = version_number or analysis.get("draft_version") or 1
    return generate_prd(
        requirements=analysis.get("requirements", ""),
        use_ai=True,
        ai_provider=ai_provider or analysis.get("ai_provider"),
        model=model,
        intake_fields=None,
        previous_document=analysis.get("prd_document"),
        previous_brief=analysis.get("product_brief"),
        previous_version=previous_version,
        approved_version=analysis.get("approved_version"),
        answers=answers,
    )
