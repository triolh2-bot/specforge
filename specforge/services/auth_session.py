import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import requests
from cryptography.fernet import Fernet
from flask import current_app, session

from ..repositories.auth_repository import (
    clear_auth_session_tokens,
    delete_auth_session_credential,
    get_auth_session_credential,
    upsert_auth_session_credential,
)
from ..repositories.workspace_repository import create_workspace


def utcnow():
    return datetime.now(timezone.utc)


def build_fernet():
    secret = current_app.config["TOKEN_ENCRYPTION_SECRET"].encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def get_or_create_auth_session_id():
    auth_session_id = session.get("auth_session_id")
    if not auth_session_id:
        auth_session_id = secrets.token_urlsafe(32)
        session["auth_session_id"] = auth_session_id
    session.permanent = True
    return auth_session_id


def ensure_workspace_context():
    auth_session_id = get_or_create_auth_session_id()
    credential = get_auth_session_credential(auth_session_id)
    if credential:
        session["workspace_id"] = credential.workspace_id
        session["workspace_role"] = credential.role
        return {
            "auth_session_id": auth_session_id,
            "workspace_id": credential.workspace_id,
            "role": credential.role,
        }

    workspace = create_workspace()
    credential = upsert_auth_session_credential(
        auth_session_id=auth_session_id,
        provider="session",
        encrypted_access_token=None,
        encrypted_refresh_token=None,
        token_expires_at=None,
        workspace_id=workspace.id,
        role="owner",
    )
    session["workspace_id"] = workspace.id
    session["workspace_role"] = credential.role
    return {
        "auth_session_id": auth_session_id,
        "workspace_id": workspace.id,
        "role": credential.role,
    }


def get_current_workspace_context():
    return ensure_workspace_context()


def rotate_auth_session():
    previous_state = session.get("oauth_state")
    previous_auth_session_id = session.get("auth_session_id")
    previous_credential = get_auth_session_credential(previous_auth_session_id) if previous_auth_session_id else None
    session.clear()
    session.permanent = True
    auth_session_id = get_or_create_auth_session_id()
    if previous_state:
        session["oauth_state"] = previous_state
    if previous_credential:
        upsert_auth_session_credential(
            auth_session_id=auth_session_id,
            provider=previous_credential.provider,
            encrypted_access_token=None,
            encrypted_refresh_token=None,
            token_expires_at=None,
            workspace_id=previous_credential.workspace_id,
            role=previous_credential.role,
        )
        delete_auth_session_credential(previous_auth_session_id)
        session["workspace_id"] = previous_credential.workspace_id
        session["workspace_role"] = previous_credential.role
    else:
        ensure_workspace_context()
    return auth_session_id


def store_minimax_tokens(access_token, refresh_token=None, expires_in=3600):
    context = ensure_workspace_context()
    auth_session_id = context["auth_session_id"]
    fernet = build_fernet()
    credential = upsert_auth_session_credential(
        auth_session_id=auth_session_id,
        provider="minimax",
        encrypted_access_token=fernet.encrypt(access_token.encode("utf-8")).decode("utf-8"),
        encrypted_refresh_token=fernet.encrypt(refresh_token.encode("utf-8")).decode("utf-8") if refresh_token else None,
        token_expires_at=utcnow() + timedelta(seconds=expires_in),
        workspace_id=context["workspace_id"],
        role=context["role"],
    )
    session["minimax_authenticated"] = True
    session.permanent = True
    return credential


def clear_minimax_tokens():
    context = ensure_workspace_context()
    clear_auth_session_tokens(context["auth_session_id"])
    session["minimax_authenticated"] = False
    session.pop("oauth_state", None)
    session["workspace_id"] = context["workspace_id"]
    session["workspace_role"] = context["role"]


def get_minimax_auth_status():
    context = ensure_workspace_context()
    auth_session_id = context["auth_session_id"]

    credential = get_auth_session_credential(auth_session_id)
    if not credential or not credential.encrypted_access_token:
        return {  # nosec B105 — integer literal, not a password
            "authenticated": False,
            "token_expires_in": 0,
            "workspace_id": context["workspace_id"],
            "role": context["role"],
        }

    expires_at = _ensure_aware(credential.token_expires_at)
    expires_in = max(0, int((expires_at - utcnow()).total_seconds())) if expires_at else 0
    return {
        "authenticated": True,
        "token_expires_in": expires_in,
        "workspace_id": credential.workspace_id,
        "role": credential.role,
    }


def get_valid_minimax_access_token():
    auth_session_id = ensure_workspace_context()["auth_session_id"]

    credential = get_auth_session_credential(auth_session_id)
    if not credential or not credential.encrypted_access_token:
        return None

    expires_at = _ensure_aware(credential.token_expires_at)
    if expires_at and expires_at <= utcnow():
        refreshed = refresh_minimax_access_token(auth_session_id, credential)
        if not refreshed:
            return None
        credential = refreshed

    return build_fernet().decrypt(credential.encrypted_access_token.encode("utf-8")).decode("utf-8")


def refresh_minimax_access_token(auth_session_id, credential=None):
    credential = credential or get_auth_session_credential(auth_session_id)
    if not credential or not credential.encrypted_refresh_token:
        return None

    refresh_token = build_fernet().decrypt(credential.encrypted_refresh_token.encode("utf-8")).decode("utf-8")
    data = {
        "client_id": current_app.config["MINIMAX_CLIENT_ID"],
        "client_secret": current_app.config["MINIMAX_CLIENT_SECRET"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        response = requests.post(current_app.config["MINIMAX_TOKEN_URL"], data=data, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    access_token = payload.get("access_token")
    if not access_token:
        return None

    new_refresh_token = payload.get("refresh_token", refresh_token)
    expires_in = payload.get("expires_in", 3600)
    return upsert_auth_session_credential(
        auth_session_id=auth_session_id,
        provider="minimax",
        encrypted_access_token=build_fernet().encrypt(access_token.encode("utf-8")).decode("utf-8"),
        encrypted_refresh_token=build_fernet().encrypt(new_refresh_token.encode("utf-8")).decode("utf-8"),
        token_expires_at=utcnow() + timedelta(seconds=expires_in),
        workspace_id=credential.workspace_id,
        role=credential.role,
    )


def _ensure_aware(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)
