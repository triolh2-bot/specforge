"""Role hierarchy, permission matrix, and enforcement for workspace resources."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional

from flask import session

logger = logging.getLogger(__name__)


def _ensure_workspace_context():
    """Lazy import to avoid circular dependency."""
    from ..services.auth_session import ensure_workspace_context
    return ensure_workspace_context()


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

class WorkspaceRole(str, enum.Enum):
    """Workspace roles ordered from least to most privileged."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"
    OWNER = "owner"


# Role hierarchy: each role includes all permissions of roles below it
_ROLE_LEVEL = {
    WorkspaceRole.VIEWER: 0,
    WorkspaceRole.EDITOR: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}

ROLES = [r.value for r in WorkspaceRole]


def role_level(role: str) -> int:
    """Return the numeric level of a role (higher = more privileged)."""
    return _ROLE_LEVEL.get(WorkspaceRole(role), -1)


def is_at_least(role: str, required: str) -> bool:
    """Check whether *role* meets or exceeds *required*."""
    return role_level(role) >= role_level(required)


# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Permission:
    """A single named permission."""
    name: str
    description: str = ""


# Define all permissions
PERM = type("PERM", (), {
    # Analysis operations
    "READ_ANALYSIS": Permission("read:analysis", "View analyses and their details"),
    "WRITE_ANALYSIS": Permission("write:analysis", "Create and update analyses"),
    "DELETE_ANALYSIS": Permission("delete:analysis", "Delete analyses"),
    # Job operations
    "READ_JOBS": Permission("read:jobs", "View job status and results"),
    "WRITE_JOBS": Permission("write:jobs", "Enqueue and manage analysis jobs"),
    # Export operations
    "READ_EXPORTS": Permission("read:exports", "View export history"),
    "WRITE_EXPORTS": Permission("write:exports", "Create exports"),
    # Workspace operations
    "READ_WORKSPACE": Permission("read:workspace", "View workspace settings and members"),
    "MANAGE_MEMBERS": Permission("manage:members", "Invite, update roles, and remove members"),
    "MANAGE_SETTINGS": Permission("manage:settings", "Update workspace name and settings"),
    "DELETE_WORKSPACE": Permission("delete:workspace", "Delete the workspace entirely"),
    # AI provider operations
    "USE_AI": Permission("use:ai", "Use AI enhancement features"),
})

# Role → permissions mapping
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    WorkspaceRole.VIEWER.value: {
        PERM.READ_ANALYSIS.name,
        PERM.READ_JOBS.name,
        PERM.READ_EXPORTS.name,
        PERM.READ_WORKSPACE.name,
    },
    WorkspaceRole.EDITOR.value: {
        PERM.READ_ANALYSIS.name,
        PERM.WRITE_ANALYSIS.name,
        PERM.READ_JOBS.name,
        PERM.WRITE_JOBS.name,
        PERM.READ_EXPORTS.name,
        PERM.WRITE_EXPORTS.name,
        PERM.READ_WORKSPACE.name,
        PERM.USE_AI.name,
    },
    WorkspaceRole.ADMIN.value: {
        PERM.READ_ANALYSIS.name,
        PERM.WRITE_ANALYSIS.name,
        PERM.DELETE_ANALYSIS.name,
        PERM.READ_JOBS.name,
        PERM.WRITE_JOBS.name,
        PERM.READ_EXPORTS.name,
        PERM.WRITE_EXPORTS.name,
        PERM.READ_WORKSPACE.name,
        PERM.MANAGE_MEMBERS.name,
        PERM.MANAGE_SETTINGS.name,
        PERM.USE_AI.name,
    },
    WorkspaceRole.OWNER.value: {
        PERM.READ_ANALYSIS.name,
        PERM.WRITE_ANALYSIS.name,
        PERM.DELETE_ANALYSIS.name,
        PERM.READ_JOBS.name,
        PERM.WRITE_JOBS.name,
        PERM.READ_EXPORTS.name,
        PERM.WRITE_EXPORTS.name,
        PERM.READ_WORKSPACE.name,
        PERM.MANAGE_MEMBERS.name,
        PERM.MANAGE_SETTINGS.name,
        PERM.DELETE_WORKSPACE.name,
        PERM.USE_AI.name,
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check whether *role* grants *permission*."""
    return permission in _ROLE_PERMISSIONS.get(role, set())


def get_role_permissions(role: str) -> set[str]:
    """Return all permissions granted to *role*."""
    return set(_ROLE_PERMISSIONS.get(role, set()))


def get_minimum_role_for_permission(permission: str) -> str:
    """Return the lowest role that has *permission*."""
    for role in [WorkspaceRole.VIEWER, WorkspaceRole.EDITOR, WorkspaceRole.ADMIN, WorkspaceRole.OWNER]:
        if has_permission(role.value, permission):
            return role.value
    raise ValueError(f"Unknown permission: {permission}")


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_session_role() -> Optional[str]:
    """Get the current user's role from the session."""
    return session.get("workspace_role")


def get_session_workspace_id() -> Optional[str]:
    """Get the current workspace ID from the session."""
    return session.get("workspace_id")


# ---------------------------------------------------------------------------
# Authorization decorator
# ---------------------------------------------------------------------------

@dataclass
class AuthorizationError(Exception):
    """Raised when authorization fails."""
    permission: str
    required_role: str
    actual_role: str
    message: str = ""

    def __str__(self) -> str:
        if self.message:
            return self.message
        return (
            f"Access denied: permission '{self.permission}' requires "
            f"role '{self.required_role}' or higher (current: '{self.actual_role}')"
        )


def require_permission(permission: str) -> Callable:
    """Decorator that enforces the user has *permission* based on their role.

    Automatically calls ``ensure_workspace_context()`` so that the workspace
    and role are set up from the auth session before checking permissions.

    Usage::

        @require_permission("write:analysis")
        def create_analysis():
            ...
    """
    required_role = get_minimum_role_for_permission(permission)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Ensure workspace context is established (sets session role)
            try:
                _ensure_workspace_context()
            except Exception as exc:
                # Fail closed: if context setup fails, deny access immediately.
                logger.debug("Workspace context setup failed in RBAC decorator: %s", exc)
                raise AuthorizationError(
                    permission=permission,
                    required_role=required_role,
                    actual_role="anonymous",
                    message="Failed to establish workspace context.",
                ) from exc

            current_role = get_session_role()
            if current_role is None:
                raise AuthorizationError(
                    permission=permission,
                    required_role=required_role,
                    actual_role="anonymous",
                    message="Authentication required",
                )
            if not has_permission(current_role, permission):
                raise AuthorizationError(
                    permission=permission,
                    required_role=required_role,
                    actual_role=current_role,
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(minimum_role: str) -> Callable:
    """Decorator that enforces the user's role is at least *minimum_role*.

    Automatically calls ``ensure_workspace_context()`` before checking.

    Usage::

        @require_role("admin")
        def manage_members():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                _ensure_workspace_context()
            except Exception as exc:
                # Fail closed: if context setup fails, deny access immediately.
                logger.debug("Workspace context setup failed in require_role decorator: %s", exc)
                raise AuthorizationError(
                    permission="role_check",
                    required_role=minimum_role,
                    actual_role="anonymous",
                    message="Failed to establish workspace context.",
                ) from exc

            current_role = get_session_role()
            if current_role is None:
                raise AuthorizationError(
                    permission="role_check",
                    required_role=minimum_role,
                    actual_role="anonymous",
                    message="Authentication required",
                )
            if not is_at_least(current_role, minimum_role):
                raise AuthorizationError(
                    permission="role_check",
                    required_role=minimum_role,
                    actual_role=current_role,
                    message=f"Role '{current_role}' is insufficient (need '{minimum_role}' or higher)",
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Resource ownership helper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResourceAccess:
    """Result of checking whether a user can access a specific resource."""

    allowed: bool
    reason: str = ""
    role: Optional[str] = None


def check_resource_access(
    resource_workspace_id: Optional[str],
    permission: str,
) -> ResourceAccess:
    """Check whether the current session user can access a resource.

    This checks both workspace ownership (resource must be in user's workspace)
    and role-based permissions.
    """
    current_role = get_session_role()
    current_workspace = get_session_workspace_id()

    if current_role is None:
        return ResourceAccess(allowed=False, reason="No authenticated session")

    if current_workspace is None:
        return ResourceAccess(allowed=False, reason="No workspace context")

    # Workspace isolation check
    if resource_workspace_id and resource_workspace_id != current_workspace:
        return ResourceAccess(
            allowed=False,
            reason=f"Resource belongs to workspace {resource_workspace_id}, not {current_workspace}",
        )

    # Role-based permission check
    if not has_permission(current_role, permission):
        required = get_minimum_role_for_permission(permission)
        return ResourceAccess(
            allowed=False,
            reason=f"Role '{current_role}' lacks '{permission}' (requires '{required}')",
            role=current_role,
        )

    return ResourceAccess(allowed=True, role=current_role)


def enforce_resource_access(resource_workspace_id: Optional[str], permission: str) -> None:
    """Like check_resource_access but raises AuthorizationError on failure."""
    result = check_resource_access(resource_workspace_id, permission)
    if not result.allowed:
        raise AuthorizationError(
            permission=permission,
            required_role=get_minimum_role_for_permission(permission),
            actual_role=result.role or "anonymous",
            message=result.reason,
        )
