import logging

from flask import current_app, session

from .domain_analysis import (
    calculate_rms,
    detect_conflicts,
    detect_domain,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
)
from .minimax import call_minimax_chat_api

logger = logging.getLogger(__name__)


def generate_prd(client_input, use_ai=False, ai_provider="minimax"):
    domain = detect_domain(client_input)
    missing_features = detect_missing_features(domain, client_input)
    questions = generate_questions(domain, client_input, missing_features)
    implied_users = detect_implied_users(client_input)
    conflicts = detect_conflicts(client_input)
    rms = calculate_rms(client_input, domain)

    ai_enhanced = None
    minimax_result = None

    if use_ai and (current_app.config["MINIMAX_API_KEY"] or session.get("minimax_authenticated")):
        minimax_result = call_minimax_chat_api(client_input, domain, missing_features)

        if minimax_result:
            ai_enhanced = {"status": "success", "provider": ai_provider, "data": minimax_result}
            if minimax_result.get("clarification_questions"):
                questions = minimax_result["clarification_questions"][:5]
        else:
            logger.info("MiniMax API enhancement failed, using rule-based fallback")
            ai_enhanced = {
                "status": "fallback",
                "provider": ai_provider,
                "message": "Using rule-based analysis (AI enhancement unavailable)",
            }

    prd_summary = client_input[:300]
    tech_stack = None
    risks = [
        "Scope creep from unclear requirements",
        "Third-party API integration challenges",
        "Timeline delays from dependencies",
    ]
    timeline = "To be determined"

    if minimax_result:
        prd_summary = minimax_result.get("prd_summary", prd_summary)
        tech_stack = minimax_result.get("tech_stack_recommendation")
        if minimax_result.get("risk_factors"):
            risks = minimax_result["risk_factors"][:3]
        timeline = minimax_result.get("estimated_timeline", timeline)

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
        "ai_providers": {
            "minimax": {
                "oauth_enabled": bool(current_app.config["MINIMAX_CLIENT_ID"]),
                "api_key_enabled": bool(current_app.config["MINIMAX_API_KEY"]),
                "models": [current_app.config["MINIMAX_MODEL"], "abab6.5s-chat", "abab6-chat"],
            }
        },
    }
