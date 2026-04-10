"""Workspace member management endpoints."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from flask import Blueprint, request

from ..extensions import db
from ..http import error_response, json_response
from ..models import AuthSessionCredential, Workspace
from ..services.auth_session import ensure_workspace_context
from ..services.rbac import (
    PERM,
    AuthorizationError,
    WorkspaceRole,
    check_resource_access,
    enforce_resource_access,
    get_session_workspace_id,
    require_permission,
    ROLES,
)

members_bp = Blueprint("members", __name__)


def _find_member(workspace_id: str, member_id: str):
    """Find a workspace member by auth_session_id."""
    return AuthSessionCredential.query.filter_by(
        workspace_id=workspace_id,
        auth_session_id=member_id,
    ).first()


def _list_workspace_members(workspace_id: str):
    """List all credentials in a workspace."""
    return AuthSessionCredential.query.filter_by(workspace_id=workspace_id).all()


def _generate_invite_token() -> str:
    """Generate a one-time invite token."""
    return secrets.token_urlsafe(32)


@members_bp.route("/api/workspace/members", methods=["GET"])
@require_permission(PERM.READ_WORKSPACE.name)
def list_members():
    """List all members of the current workspace."""
    workspace_id = get_session_workspace_id()
    members = _list_workspace_members(workspace_id)

    result = []
    for m in members:
        result.append({
            "member_id": m.auth_session_id,
            "masked_id": m.auth_session_id[:8] + "..." + m.auth_session_id[-4:],
            "provider": m.provider,
            "role": m.role,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            "token_expires_at": m.token_expires_at.isoformat() if m.token_expires_at else None,
            "is_active": bool(m.encrypted_access_token),
        })

    return json_response({
        "workspace_id": workspace_id,
        "members": result,
        "count": len(result),
    })


@members_bp.route("/api/workspace/members/<member_id>/role", methods=["PUT"])
@require_permission(PERM.MANAGE_MEMBERS.name)
def update_member_role(member_id: str):
    """Update a member's role. Only available to admins and owners."""
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")

    if new_role not in ROLES:
        return error_response(
            f"Invalid role '{new_role}'. Must be one of: {', '.join(ROLES)}",
            status=400,
            code="invalid_role",
            details={"valid_roles": ROLES},
        )

    workspace_id = get_session_workspace_id()
    member = _find_member(workspace_id, member_id)

    if not member:
        return error_response("Member not found", status=404, code="member_not_found")

    # Prevent self-demotion of the last owner
    if member.role == WorkspaceRole.OWNER.value and new_role != WorkspaceRole.OWNER.value:
        other_owners = AuthSessionCredential.query.filter_by(
            workspace_id=workspace_id,
            role=WorkspaceRole.OWNER.value,
        ).filter(AuthSessionCredential.id != member.id).count()
        if other_owners == 0:
            return error_response(
                "Cannot demote the last owner. Transfer ownership first.",
                status=400,
                code="last_owner",
            )

    old_role = member.role
    member.role = new_role
    db.session.commit()

    return json_response({
        "member_id": member_id,
        "old_role": old_role,
        "new_role": new_role,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


@members_bp.route("/api/workspace/members/<member_id>", methods=["DELETE"])
@require_permission(PERM.MANAGE_MEMBERS.name)
def remove_member(member_id: str):
    """Remove a member from the workspace."""
    workspace_id = get_session_workspace_id()
    member = _find_member(workspace_id, member_id)

    if not member:
        return error_response("Member not found", status=404, code="member_not_found")

    # Prevent removing the last owner
    if member.role == WorkspaceRole.OWNER.value:
        other_owners = AuthSessionCredential.query.filter_by(
            workspace_id=workspace_id,
            role=WorkspaceRole.OWNER.value,
        ).filter(AuthSessionCredential.id != member.id).count()
        if other_owners == 0:
            return error_response(
                "Cannot remove the last owner. Transfer ownership first.",
                status=400,
                code="last_owner",
            )

    db.session.delete(member)
    db.session.commit()

    return json_response({
        "member_id": member_id,
        "removed": True,
        "removed_at": datetime.now(timezone.utc).isoformat(),
    })


@members_bp.route("/api/workspace/members/me", methods=["GET"])
def get_my_role():
    """Get the current user's role and workspace info."""
    context = ensure_workspace_context()
    workspace_id = context.get("workspace_id")

    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return error_response("Workspace not found", status=404, code="workspace_not_found")

    return json_response({
        "workspace_id": workspace_id,
        "workspace_name": workspace.name,
        "role": context.get("role", "viewer"),
    })
