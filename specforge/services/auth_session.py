import base64
import hashlib
import secrets
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from flask import current_app, session

from ..repositories.auth_repository import (
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
    previous_auth_session_id = session.get("auth_session_id")
    # In a real app we might want to migrate state, but here we'll just clear
    session.clear()
    session.permanent = True
    return get_or_create_auth_session_id()


def get_auth_status():
    """Return the current session's workspace-backed auth status."""
    context = ensure_workspace_context()
    auth_session_id = context["auth_session_id"]

    credential = get_auth_session_credential(auth_session_id)
    return {
        "authenticated": bool(credential),
        "token_expires_in": 0,
        "workspace_id": context["workspace_id"],
        "role": context["role"],
    }


def _ensure_aware(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)
