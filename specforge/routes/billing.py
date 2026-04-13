"""Billing and subscription routes with PayPal integration."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, request, url_for

from ..extensions import db
from ..http import error_response, json_response
from ..models import WorkspaceSubscription
from ..services.auth_session import ensure_workspace_context
from ..services.billing import (
    PLANS,
    check_provider_allowed,
    check_quota,
    get_quota_status,
    get_plan_limits,
    QuotaExceededError,
)
from ..services.paypal import (
    activate_subscription,
    cancel_subscription as paypal_cancel_subscription,
    create_paypal_subscription,
    handle_paypal_webhook_event,
    is_paypal_configured,
    is_paypal_plan_available,
    verify_paypal_webhook_signature,
)
from ..services.rbac import PERM, require_permission, require_role

billing_bp = Blueprint("billing", __name__)


# ---------------------------------------------------------------------------
# Plan listing and quota
# ---------------------------------------------------------------------------

@billing_bp.route("/api/billing/quota", methods=["GET"])
def get_quota():
    """Return current quota usage and limits for the workspace."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    status = get_quota_status(workspace_id)
    return json_response(status)


@billing_bp.route("/api/billing/plans", methods=["GET"])
def list_plans():
    """Return all available billing plans with PayPal checkout info."""
    paypal_configured = is_paypal_configured()
    plans = {}
    for name, limits in PLANS.items():
        plan_data = {
            "name": name,
            "analyses_per_month": limits.analyses_per_month,
            "ai_enhancements_per_month": limits.ai_enhancements_per_month,
            "exports_per_month": limits.exports_per_month,
            "max_workspace_members": limits.max_workspace_members,
            "share_link_max_age_days": limits.share_link_max_age_days,
            "ai_providers": list(limits.ai_providers),
            "priority_queue": limits.priority_queue,
        }

        if name == "free":
            plan_data["price"] = "Free"
            plan_data["checkout_available"] = False
        else:
            price_key = f"PAYPAL_PLAN_PRICE_{name.upper()}"
            plan_data["price"] = current_app.config.get(price_key) or "Contact sales"
            plan_data["checkout_available"] = is_paypal_plan_available(name)

        plans[name] = plan_data

    return json_response({
        "plans": plans,
        "billing": {
            "provider": "paypal",
            "configured": paypal_configured,
        },
    })


# ---------------------------------------------------------------------------
# PayPal Checkout flow
# ---------------------------------------------------------------------------

@billing_bp.route("/api/billing/subscribe", methods=["POST"])
@require_role("admin")
def subscribe():
    """Initiate a PayPal subscription for the current workspace.

    Request body: { "plan": "pro" | "enterprise" }
    Response: { "approval_url": "https://paypal.com/..." }
    """
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    data = request.get_json(silent=True) or {}
    plan_name = data.get("plan", "pro")

    if plan_name not in ("pro", "enterprise"):
        return error_response(
            f"Invalid plan '{plan_name}'. Choose 'pro' or 'enterprise'.",
            status=400,
            code="invalid_plan",
        )

    if not is_paypal_configured():
        return error_response(
            "PayPal billing is not configured yet. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to enable upgrades.",
            status=503,
            code="billing_unavailable",
        )

    if not is_paypal_plan_available(plan_name):
        return error_response(
            f"The '{plan_name}' plan is not configured for PayPal checkout yet. Add PAYPAL_PLAN_ID_{plan_name.upper()} to enable it.",
            status=503,
            code="plan_unavailable",
        )

    # Build return/cancel URLs
    base_url = request.url_root.rstrip("/")
    return_url = f"{base_url}/api/billing/paypal/return"
    cancel_url = f"{base_url}/api/billing/paypal/cancel"

    result = create_paypal_subscription(
        workspace_id=workspace_id,
        plan_name=plan_name,
        payer_email="",  # PayPal will prompt for email
        return_url=return_url,
        cancel_url=cancel_url,
    )

    if not result:
        return error_response(
            "Failed to create PayPal subscription. Please try again or contact support.",
            status=500,
            code="paypal_error",
        )

    return json_response({
        "approval_url": result["approval_url"],
        "subscription_id": result["subscription_id"],
        "plan": plan_name,
        "workspace_id": workspace_id,
    })


@billing_bp.route("/api/billing/paypal/return", methods=["GET"])
def paypal_return():
    """Handle return from PayPal after subscription approval."""
    token = request.args.get("token", "")
    # In production, verify the token and activate the subscription
    # For now, redirect to settings with success flag
    return redirect("/?payment=success")


@billing_bp.route("/api/billing/paypal/cancel", methods=["GET"])
def paypal_cancel():
    """Handle cancellation from PayPal checkout."""
    return redirect("/?payment=cancelled")


@billing_bp.route("/api/billing/cancel", methods=["POST"])
@require_role("admin")
def cancel_subscription():
    """Cancel the current workspace subscription."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Cancelled by user")

    success = paypal_cancel_subscription(workspace_id, reason)
    if not success:
        return error_response(
            "No active PayPal subscription found for this workspace.",
            status=404,
            code="no_subscription",
        )

    return json_response({
        "cancelled": True,
        "workspace_id": workspace_id,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# PayPal Webhook
# ---------------------------------------------------------------------------

@billing_bp.route("/api/billing/webhooks/paypal", methods=["POST"])
def paypal_webhook():
    """Handle PayPal webhook events for subscription lifecycle."""
    if not verify_paypal_webhook_signature():
        return json_response({"error": "Invalid webhook signature"}, status=401)

    event = request.get_json(silent=True)
    if not event:
        return json_response({"error": "Invalid event body"}, status=400)

    try:
        handle_paypal_webhook_event(event)
        return json_response({"status": "ok"})
    except Exception as exc:
        # Always return 200 to PayPal to prevent retries
        return json_response({"status": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Quota check endpoints
# ---------------------------------------------------------------------------

@billing_bp.route("/api/billing/quota/check", methods=["POST"])
def check_quota_endpoint():
    """Check whether a specific action would exceed quota (dry run)."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    data = request.get_json(silent=True) or {}
    metric = data.get("metric")

    if not metric:
        return error_response("metric is required", status=400, code="missing_metric")

    try:
        check_quota(workspace_id, metric)
        return json_response({"allowed": True, "metric": metric})
    except QuotaExceededError as exc:
        return json_response({
            "allowed": False,
            "metric": exc.metric,
            "limit": exc.limit,
            "current": exc.current,
            "plan": exc.plan,
        })


@billing_bp.route("/api/billing/provider/check", methods=["POST"])
def check_provider_endpoint():
    """Check whether a provider is allowed for the workspace's plan."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    data = request.get_json(silent=True) or {}
    provider = data.get("provider")

    if not provider:
        return error_response("provider is required", status=400, code="missing_provider")

    allowed = check_provider_allowed(workspace_id, provider)
    return json_response({"allowed": allowed, "provider": provider})


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------

@billing_bp.route("/api/billing/subscription", methods=["GET"])
def get_subscription():
    """Return the current workspace subscription details."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    sub = WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).first()
    if not sub:
        return json_response({
            "plan": "free",
            "status": "none",
            "provider": None,
        })

    return json_response({
        "plan": sub.plan,
        "status": sub.status,
        "provider": sub.provider,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "canceled_at": sub.canceled_at.isoformat() if sub.canceled_at else None,
    })
