"""Analytics dashboard routes — funnel, domain distribution, provider usage, and trends."""

from __future__ import annotations

from flask import Blueprint, request

from ..http import error_response, json_response
from ..services.analytics import (
    get_domain_distribution,
    get_funnel_summary,
    get_provider_usage,
    get_usage_over_time,
)
from ..services.auth_session import ensure_workspace_context
from ..services.rbac import PERM, enforce_resource_access

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics/funnel", methods=["GET"])
def analytics_funnel():
    """Return funnel metrics for the current workspace."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.READ_WORKSPACE.name)

    days = min(request.args.get("days", 30, type=int), 365)
    summary = get_funnel_summary(workspace_id=workspace_id, days=days)
    return json_response({"funnel": summary, "period_days": days})


@analytics_bp.route("/api/analytics/domains", methods=["GET"])
def analytics_domains():
    """Return domain distribution for analyses."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.READ_WORKSPACE.name)

    days = min(request.args.get("days", 30, type=int), 365)
    distribution = get_domain_distribution(workspace_id=workspace_id, days=days)
    return json_response({"domains": distribution, "period_days": days})


@analytics_bp.route("/api/analytics/providers", methods=["GET"])
def analytics_providers():
    """Return provider usage statistics."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.READ_WORKSPACE.name)

    days = min(request.args.get("days", 30, type=int), 365)
    providers = get_provider_usage(workspace_id=workspace_id, days=days)
    return json_response({"providers": providers, "period_days": days})


@analytics_bp.route("/api/analytics/trends", methods=["GET"])
def analytics_trends():
    """Return daily usage trends."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.READ_WORKSPACE.name)

    days = min(request.args.get("days", 30, type=int), 365)
    trends = get_usage_over_time(workspace_id=workspace_id, days=days)
    return json_response({"trends": trends, "period_days": days})
