"""Prompt management and guardrails for AI interactions.

Provides versioned prompt templates, output schema validation, and
prompt-injection mitigation so that AI orchestration stays predictable,
testable, and resilient to malformed or hostile user input.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptTemplate:
    """A versioned prompt template with optional system instruction."""

    name: str
    version: str
    system_prompt: str
    user_template: str


# Central registry of prompt templates
_PROMPT_REGISTRY: dict[str, PromptTemplate] = {}


def register_template(template: PromptTemplate) -> None:
    """Register a prompt template.  Latest version wins for a given *name*."""
    _PROMPT_REGISTRY[f"{template.name}:{template.version}"] = template


def get_template(name: str, version: Optional[str] = None) -> Optional[PromptTemplate]:
    """Retrieve a prompt template by name (and optionally version)."""
    if version:
        return _PROMPT_REGISTRY.get(f"{name}:{version}")
    # Return the latest version (highest version string for the given name)
    matches = {k: v for k, v in _PROMPT_REGISTRY.items() if k.startswith(f"{name}:")}
    if not matches:
        return None
    return max(matches.values(), key=lambda t: t.version)


def list_template_versions(name: str) -> list[str]:
    """List all registered versions of a template."""
    prefix = f"{name}:"
    return sorted(k[len(prefix):] for k in _PROMPT_REGISTRY if k.startswith(prefix))


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

PRD_ENHANCEMENT_V1 = PromptTemplate(
    name="prd_enhancement",
    version="1.0",
    system_prompt=(
        "You are an expert software architect and product manager. "
        "Provide structured, actionable analysis in valid JSON format only. "
        "Do NOT include any commentary outside the JSON object."
    ),
    user_template=(
        "Analyze the following software requirements and provide a structured enhancement analysis.\n\n"
        "REQUIREMENTS:\n{requirements}\n\n"
        "DETECTED DOMAIN: {domain}\n\n"
        "MISSING FEATURES DETECTED:\n{missing_features}\n\n"
        'Please provide a structured JSON response with the following fields:\n\n'
        '1. "prd_summary": A comprehensive 2-3 paragraph summary of the project that would serve as a PRD overview. '
        "Include the purpose, target users, and key value propositions.\n\n"
        '2. "clarification_questions": An array of exactly 5 smart, specific clarification questions '
        "tailored to these requirements. Questions should be actionable and help scope the project better.\n\n"
        '3. "tech_stack_recommendation": A recommended technology stack for the {domain} domain, '
        "including frontend, backend, database, and any specific frameworks/libraries.\n\n"
        '4. "risk_factors": An array of exactly 3 specific risk factors relevant to this particular project '
        "based on the requirements and domain.\n\n"
        '5. "estimated_timeline": A realistic development timeline estimate (e.g., "8-12 weeks", "3-4 months") '
        "with brief justification.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        "{{\n"
        '  "prd_summary": "string",\n'
        '  "clarification_questions": ["q1", "q2", "q3", "q4", "q5"],\n'
        '  "tech_stack_recommendation": "string",\n'
        '  "risk_factors": ["risk1", "risk2", "risk3"],\n'
        '  "estimated_timeline": "string"\n'
        "}}"
    ),
)

REQUIREMENT_ENHANCE_V1 = PromptTemplate(
    name="requirement_enhance",
    version="1.0",
    system_prompt=(
        "You are a senior software architect helping to refine project requirements. "
        "Provide concise, actionable recommendations."
    ),
    user_template=(
        "Analyze these requirements and provide enhancement suggestions:\n\n"
        "Requirements: {requirements}\n\n"
        "Provide:\n"
        "1. Missing technical components\n"
        "2. Security considerations\n"
        "3. Scalability recommendations\n"
        "4. User experience improvements\n"
        "5. Potential risks\n\n"
        "Be concise and actionable."
    ),
)


PRD_REFINEMENT_V1 = PromptTemplate(
    name="prd_refinement",
    version="1.0",
    system_prompt=(
        "You are an expert software architect and product manager. "
        "Provide structured, actionable analysis in valid JSON format only. "
        "Do NOT include any commentary outside the JSON object."
    ),
    user_template=(
        "Refine the PRD based on the original requirements and the user's answers to clarification questions.\n\n"
        "ORIGINAL REQUIREMENTS:\n{requirements}\n\n"
        "DETECTED DOMAIN: {domain}\n\n"
        "CLARIFICATION Q&A:\n{qa_context}\n\n"
        'Please provide a structured JSON response with the following fields:\n\n'
        '1. "prd_summary": A comprehensive 2-3 paragraph summary of the project that serves as a refined PRD overview. '
        "Integrate insights from the Q&A context.\n\n"
        '2. "tech_stack_recommendation": A recommended technology stack for the {domain} domain, tailored to the Q&A constraints.\n\n'
        '3. "risk_factors": An array of exactly 3 specific risk factors relevant to this finalized scope.\n\n'
        '4. "estimated_timeline": A realistic development timeline estimate based on the final scope.\n\n'
        "Return ONLY valid JSON in this exact format:\n"
        "{{\n"
        '  "prd_summary": "string",\n'
        '  "tech_stack_recommendation": "string",\n'
        '  "risk_factors": ["risk1", "risk2", "risk3"],\n'
        '  "estimated_timeline": "string"\n'
        "}}"
    ),
)


BRIEF_GENERATION_V1 = PromptTemplate(
    name="brief_generation",
    version="1.0",
    system_prompt=(
        "You are an expert product manager and technical writer. "
        "Your job is to write detailed, professional software project requirements briefs. "
        "Return ONLY a plain text requirements brief — no JSON, no markdown headers, no bullet-list preamble. "
        "Write it as a well-structured professional paragraph description a developer can act on."
    ),
    user_template=(
        "Generate a detailed requirements brief for the following project idea.\n\n"
        "Project Name: {project_name}\n"
        "Project Type: {project_type}\n"
        "Core Idea: {core_idea}\n"
        "Target Audience: {target_audience}\n"
        "Key Features: {key_features}\n\n"
        "Write a comprehensive 3-5 paragraph requirements brief that covers:\n"
        "1. The overall purpose and goals of the project\n"
        "2. The target audience and their needs\n"
        "3. Core features and functionality in detail\n"
        "4. Technical requirements and integrations (authentication, payments, APIs, etc.)\n"
        "5. Admin/management capabilities needed\n\n"
        "Write the brief as flowing professional paragraphs (not bullet points). "
        "Be specific, concrete, and actionable. A developer should be able to start "
        "building from this brief alone."
    ),
)


def register_builtin_templates() -> None:
    """Register all built-in prompt templates."""
    for template in (PRD_ENHANCEMENT_V1, REQUIREMENT_ENHANCE_V1, PRD_REFINEMENT_V1, BRIEF_GENERATION_V1):
        register_template(template)


# ---------------------------------------------------------------------------
# Output schema validation
# ---------------------------------------------------------------------------

# JSON schema for the PRD refinement response
PRD_REFINEMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["prd_summary"],
    "properties": {
        "prd_summary": {"type": "string", "minLength": 10, "maxLength": 5000},
        "tech_stack_recommendation": {"type": "string", "maxLength": 2000},
        "risk_factors": {
            "type": "array",
            "items": {"type": "string", "maxLength": 500},
            "maxItems": 10,
        },
        "estimated_timeline": {"type": "string", "maxLength": 200},
    },
    "additionalProperties": True,
}


# JSON schema for the PRD enhancement response
PRD_ENHANCEMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["prd_summary", "clarification_questions"],
    "properties": {
        "prd_summary": {"type": "string", "minLength": 10, "maxLength": 5000},
        "clarification_questions": {
            "type": "array",
            "items": {"type": "string", "minLength": 5, "maxLength": 500},
            "minItems": 1,
            "maxItems": 10,
        },
        "tech_stack_recommendation": {"type": "string", "maxLength": 2000},
        "risk_factors": {
            "type": "array",
            "items": {"type": "string", "maxLength": 500},
            "maxItems": 10,
        },
        "estimated_timeline": {"type": "string", "maxLength": 200},
    },
    "additionalProperties": True,
}


def validate_output(data: Any, schema: dict[str, Any]) -> list[str]:
    """Validate *data* against a JSON-schema-like *schema*.

    Returns a list of error messages (empty list means valid).
    This is a lightweight validator — not a full JSON Schema implementation,
    but covers the common cases used in this project.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Expected a JSON object (dict)"]

    # Check required fields
    for required_field in schema.get("required", []):
        if required_field not in data:
            errors.append(f"Missing required field: {required_field}")

    # Validate properties
    properties = schema.get("properties", {})
    for prop_name, prop_schema in properties.items():
        if prop_name not in data:
            continue

        value = data[prop_name]
        prop_type = prop_schema.get("type")

        # Type check
        if prop_type == "string" and not isinstance(value, str):
            errors.append(f"Field '{prop_name}' must be a string")
        elif prop_type == "array" and not isinstance(value, list):
            errors.append(f"Field '{prop_name}' must be an array")
        elif prop_type == "integer" and not isinstance(value, int):
            errors.append(f"Field '{prop_name}' must be an integer")

        # String constraints
        if prop_type == "string" and isinstance(value, str):
            if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
                errors.append(f"Field '{prop_name}' is too short (min {prop_schema['minLength']} chars)")
            if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
                errors.append(f"Field '{prop_name}' is too long (max {prop_schema['maxLength']} chars)")

        # Array constraints
        if prop_type == "array" and isinstance(value, list):
            if "minItems" in prop_schema and len(value) < prop_schema["minItems"]:
                errors.append(f"Field '{prop_name}' has too few items (min {prop_schema['minItems']})")
            if "maxItems" in prop_schema and len(value) > prop_schema["maxItems"]:
                errors.append(f"Field '{prop_name}' has too many items (max {prop_schema['maxItems']})")

            # Item validation
            items_schema = prop_schema.get("items", {})
            item_type = items_schema.get("type")
            if item_type == "string":
                for i, item in enumerate(value):
                    if not isinstance(item, str):
                        errors.append(f"Item {i} in '{prop_name}' must be a string")
                        continue
                    if "maxLength" in items_schema and len(item) > items_schema["maxLength"]:
                        errors.append(f"Item {i} in '{prop_name}' exceeds max length")
                    if "minLength" in items_schema and len(item) < items_schema["minLength"]:
                        errors.append(f"Item {i} in '{prop_name}' is too short")

    return errors


def repair_output(data: Any, schema: dict[str, Any]) -> dict[str, Any]:
    """Attempt to repair common issues in AI output.

    - Ensures required string fields are non-empty (fallback to empty string)
    - Truncates oversized arrays
    - Removes unexpected extra items from arrays
    """
    if not isinstance(data, dict):
        return {}

    repaired = dict(data)
    properties = schema.get("properties", {})

    for prop_name, prop_schema in properties.items():
        if prop_name not in repaired:
            # Provide defaults for missing required fields
            if prop_name in schema.get("required", []):
                if prop_schema.get("type") == "string":
                    repaired[prop_name] = ""
                elif prop_schema.get("type") == "array":
                    repaired[prop_name] = []
            continue

        value = repaired[prop_name]

        # Truncate arrays to maxItems
        if prop_schema.get("type") == "array" and isinstance(value, list):
            max_items = prop_schema.get("maxItems")
            if max_items and len(value) > max_items:
                repaired[prop_name] = value[:max_items]

        # Truncate strings to maxLength
        if prop_schema.get("type") == "string" and isinstance(value, str):
            max_len = prop_schema.get("maxLength")
            if max_len and len(value) > max_len:
                repaired[prop_name] = value[:max_len]

    return repaired


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)ignore\s+(previous|all|above|these)\s+(instructions|rules|prompt|system)"),
    re.compile(r"(?i)(you\s+are\s+now|pretend\s+to\s+be|act\s+as)\s+(?!an?\s+expert|a\s+senior|an?\s+architect)"),
    re.compile(r"(?i)system\s*:\s*override"),
    re.compile(r"(?i)\\n\s*(system|user|assistant)\s*:"),
    re.compile(r"(?i)disregard\s+(all\s+(prior\s+)?)?(instructions|messages|context)"),
    re.compile(r"(?i)disregard\s+(all|the\s+previous|prior)\s+(instructions|messages|context)"),
]


def detect_prompt_injection(text: str) -> list[str]:
    """Check *text* for common prompt-injection patterns.

    Returns a list of detected pattern descriptions (empty means clean).
    """
    findings: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(f"Potential injection: '{match.group(0)[:80]}'")
    return findings


def sanitize_requirements(text: str) -> str:
    """Apply basic sanitization to user-provided requirements.

    - Strip control characters (except newlines and tabs)
    - Truncate to a reasonable maximum length
    """
    max_length = 10000
    # Remove control characters except \n, \r, \t
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    if len(cleaned) > max_length:
        logger.warning("Requirements text truncated from %d to %d chars", len(cleaned), max_length)
        cleaned = cleaned[:max_length]
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_prompt(template: PromptTemplate, **kwargs: str) -> tuple[str, str]:
    """Render a prompt template with the given variables.

    Returns ``(system_prompt, user_prompt)``.
    """
    return template.system_prompt, template.user_template.format(**kwargs)
