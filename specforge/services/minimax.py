import json
import logging
import secrets
import urllib.parse

import requests
from flask import current_app, session

logger = logging.getLogger(__name__)


def generate_oauth_state():
    return secrets.token_urlsafe(32)


def get_minimax_auth_url():
    state = generate_oauth_state()
    session["oauth_state"] = state

    params = {
        "client_id": current_app.config["MINIMAX_CLIENT_ID"],
        "redirect_uri": current_app.config["MINIMAX_REDIRECT_URI"],
        "response_type": "code",
        "scope": "api:read api:write user:read",
        "state": state,
    }
    return f"{current_app.config['MINIMAX_AUTH_URL']}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code):
    data = {
        "client_id": current_app.config["MINIMAX_CLIENT_ID"],
        "client_secret": current_app.config["MINIMAX_CLIENT_SECRET"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": current_app.config["MINIMAX_REDIRECT_URI"],
    }

    try:
        response = requests.post(current_app.config["MINIMAX_TOKEN_URL"], data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as error:
        logger.error("Token exchange error: %s", error)
        return None


def call_minimax_api(endpoint, method="GET", data=None, use_api_key=False):
    headers = {"Content-Type": "application/json"}

    if use_api_key and current_app.config["MINIMAX_API_KEY"]:
        headers["Authorization"] = f"Bearer {current_app.config['MINIMAX_API_KEY']}"
    elif session.get("access_token"):
        headers["Authorization"] = f"Bearer {session.get('access_token')}"
    else:
        return None

    url = f"{current_app.config['MINIMAX_API_BASE']}/{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=30)

        response.raise_for_status()
        return response.json()
    except Exception as error:
        logger.error("API call error: %s", error)
        return None


def call_minimax_chat_api(requirements, domain, missing_features):
    if not current_app.config["MINIMAX_API_KEY"] or not current_app.config["MINIMAX_GROUP_ID"]:
        logger.warning("MiniMax API key or Group ID not configured")
        return None

    missing_features_text = "\n".join(f"- {feature}" for feature in missing_features) if missing_features else "None detected"

    prompt = f"""Analyze the following software requirements and provide a structured enhancement analysis.

REQUIREMENTS:
{requirements}

DETECTED DOMAIN: {domain}

MISSING FEATURES DETECTED:
{missing_features_text}

Please provide a structured JSON response with the following fields:

1. "prd_summary": A comprehensive 2-3 paragraph summary of the project that would serve as a PRD overview. Include the purpose, target users, and key value propositions.

2. "clarification_questions": An array of exactly 5 smart, specific clarification questions tailored to these requirements. Questions should be actionable and help scope the project better.

3. "tech_stack_recommendation": A recommended technology stack for the {domain} domain, including frontend, backend, database, and any specific frameworks/libraries.

4. "risk_factors": An array of exactly 3 specific risk factors relevant to this particular project based on the requirements and domain.

5. "estimated_timeline": A realistic development timeline estimate (e.g., "8-12 weeks", "3-4 months") with brief justification.

Return ONLY valid JSON in this exact format:
{{
  "prd_summary": "string",
  "clarification_questions": ["q1", "q2", "q3", "q4", "q5"],
  "tech_stack_recommendation": "string",
  "risk_factors": ["risk1", "risk2", "risk3"],
  "estimated_timeline": "string"
}}"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {current_app.config['MINIMAX_API_KEY']}",
    }
    payload = {
        "model": current_app.config["MINIMAX_MODEL"],
        "messages": [
            {
                "role": "system",
                "content": "You are an expert software architect and product manager. Provide structured, actionable analysis in valid JSON format only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    try:
        url = f"{current_app.config['MINIMAX_CHAT_API_URL']}?GroupId={current_app.config['MINIMAX_GROUP_ID']}"
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        if "base_resp" in result:
            status_msg = result["base_resp"].get("status_msg", "Unknown error")
            logger.warning("MiniMax API error: %s", status_msg)
            return None

        if "choices" in result and result["choices"]:
            content = result["choices"][0]["message"]["content"]
            try:
                json_start = content.find("{")
                json_end = content.rfind("}")
                if json_start != -1 and json_end != -1:
                    return json.loads(content[json_start : json_end + 1])
                logger.warning("No JSON found in MiniMax response")
                return None
            except json.JSONDecodeError as error:
                logger.error("Failed to parse MiniMax response as JSON: %s", error)
                return None

        logger.warning("Unexpected MiniMax response format")
        return None
    except requests.exceptions.Timeout:
        logger.error("MiniMax API call timed out")
        return None
    except requests.exceptions.RequestException as error:
        logger.error("MiniMax API call failed: %s", error)
        return None
    except Exception as error:
        logger.error("Unexpected error calling MiniMax API: %s", error)
        return None
