from ..extensions import db
from ..models import AuthSessionCredential


def get_auth_session_credential(auth_session_id):
    return AuthSessionCredential.query.filter_by(auth_session_id=auth_session_id).one_or_none()


def upsert_auth_session_credential(
    auth_session_id,
    provider,
    encrypted_access_token,
    encrypted_refresh_token,
    token_expires_at,
    workspace_id,
    role="owner",
):
    credential = get_auth_session_credential(auth_session_id)
    if credential is None:
        credential = AuthSessionCredential(
            auth_session_id=auth_session_id,
            provider=provider,
            workspace_id=workspace_id,
            role=role,
        )
        db.session.add(credential)

    credential.provider = provider
    credential.workspace_id = workspace_id
    credential.role = role
    credential.encrypted_access_token = encrypted_access_token
    credential.encrypted_refresh_token = encrypted_refresh_token
    credential.token_expires_at = token_expires_at
    db.session.commit()
    return credential


def delete_auth_session_credential(auth_session_id):
    credential = get_auth_session_credential(auth_session_id)
    if credential is None:
        return False
    db.session.delete(credential)
    db.session.commit()
    return True


def clear_auth_session_tokens(auth_session_id):
    credential = get_auth_session_credential(auth_session_id)
    if credential is None:
        return None
    credential.encrypted_access_token = None
    credential.encrypted_refresh_token = None
    credential.token_expires_at = None
    credential.provider = "session"
    db.session.commit()
    return credential
