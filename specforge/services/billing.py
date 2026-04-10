"""Billing plans, quota enforcement, and usage tracking.

Provides a plan-based quota system that gates access to AI enhancement,
export generation, and analysis volume. Plans are enforced both in
synchronous request paths and background jobs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from flask import session

from ..extensions import db
from ..models import QuotaUsage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanLimits:
    """Resource limits for a billing tier."""

    analyses_per_month: int
    ai_enhancements_per_month: int
    exports_per_month: int
    max_workspace_members: int
    share_link_max_age_days: int
    ai_providers: tuple[str, ...]  # allowed provider names
    priority_queue: bool = False


PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        analyses_per_month=10,
        ai_enhancements_per_month=3,
        exports_per_month=5,
        max_workspace_members=1,
        share_link_max_age_days=3,
        ai_providers=("minimax",),
    ),
    "pro": PlanLimits(
        analyses_per_month=100,
        ai_enhancements_per_month=50,
        exports_per_month=50,
        max_workspace_members=10,
        share_link_max_age_days=30,
        ai_providers=("minimax",),
        priority_queue=True,
    ),
    "enterprise": PlanLimits(
        analyses_per_month=999999,
        ai_enhancements_per_month=999999,
        exports_per_month=999999,
        max_workspace_members=999,
        share_link_max_age_days=365,
        ai_providers=("minimax",),
        priority_queue=True,
    ),
}


def get_plan_limits(plan: str) -> PlanLimits:
    """Return the limits for a given plan name."""
    return PLANS.get(plan, PLANS["free"])


# ---------------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------------

def get_session_plan() -> str:
    """Get the billing plan for the current session.

    Falls back to "free" if no plan is set.  In production this would
    be looked up from a billing provider or user record.
    """
    return session.get("billing_plan", "free")


def get_workspace_plan(workspace_id: str) -> str:
    """Get the billing plan for a workspace.

    In production this queries the workspace's subscription record.
    """
    from ..repositories.workspace_repository import get_workspace_subscription
    sub = get_workspace_subscription(workspace_id)
    if sub and sub.plan and sub.status == "active":
        return sub.plan
    return "free"


def _get_usage_count(workspace_id: str, metric: str, days: int = 30) -> int:
    """Count how many times a metric was used in the last *days* days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        QuotaUsage.query.filter_by(
            workspace_id=workspace_id,
            metric=metric,
        )
        .filter(QuotaUsage.used_at >= since)
        .count()
    )


def _record_usage(workspace_id: str, metric: str, amount: int = 1) -> None:
    """Increment usage counter for a metric."""
    usage = QuotaUsage(
        workspace_id=workspace_id,
        metric=metric,
        amount=amount,
        used_at=datetime.now(timezone.utc),
    )
    db.session.add(usage)
    db.session.commit()


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------

class QuotaExceededError(Exception):
    """Raised when a workspace has exceeded its plan limits."""

    def __init__(self, metric: str, limit: int, current: int, plan: str):
        self.metric = metric
        self.limit = limit
        self.current = current
        self.plan = plan
        super().__init__(
            f"Quota exceeded: {metric} ({current}/{limit}) on '{plan}' plan. "
            f"Upgrade to increase limits."
        )


def check_quota(workspace_id: str, metric: str, plan: Optional[str] = None) -> None:
    """Check whether the workspace has remaining quota for *metric*.

    Raises ``QuotaExceededError`` if the limit is reached.
    Respects the QUOTA_ENFORCEMENT config setting:
    - ``strict``: enforce limits
    - ``soft``: log warnings but allow
    - ``off``: skip enforcement entirely
    """
    from flask import current_app
    enforcement = current_app.config.get("QUOTA_ENFORCEMENT", "strict")

    if enforcement == "off":
        return

    if plan is None:
        plan = get_workspace_plan(workspace_id)

    limits = get_plan_limits(plan)
    metric_map = {
        "analysis": limits.analyses_per_month,
        "ai_enhancement": limits.ai_enhancements_per_month,
        "export": limits.exports_per_month,
    }

    limit = metric_map.get(metric)
    if limit is None:
        return  # Unknown metric — no enforcement

    current = _get_usage_count(workspace_id, metric)
    if current >= limit:
        if enforcement == "soft":
            logger.warning("Soft quota exceeded: %s (%d/%d) on '%s' plan", metric, current, limit, plan)
            return
        raise QuotaExceededError(metric=metric, limit=limit, current=current, plan=plan)


def consume_quota(workspace_id: str, metric: str, plan: Optional[str] = None) -> None:
    """Check and consume one unit of quota for *metric*.

    Raises ``QuotaExceededError`` if the limit is reached.
    """
    check_quota(workspace_id, metric, plan=plan)
    _record_usage(workspace_id, metric)


def get_quota_status(workspace_id: str, plan: Optional[str] = None) -> dict[str, Any]:
    """Return current quota usage for all metrics."""
    if plan is None:
        plan = get_workspace_plan(workspace_id)

    limits = get_plan_limits(plan)
    return {
        "plan": plan,
        "analyses": {
            "used": _get_usage_count(workspace_id, "analysis"),
            "limit": limits.analyses_per_month,
        },
        "ai_enhancements": {
            "used": _get_usage_count(workspace_id, "ai_enhancement"),
            "limit": limits.ai_enhancements_per_month,
        },
        "exports": {
            "used": _get_usage_count(workspace_id, "export"),
            "limit": limits.exports_per_month,
        },
        "max_workspace_members": limits.max_workspace_members,
        "allowed_providers": list(limits.ai_providers),
        "share_link_max_age_days": limits.share_link_max_age_days,
    }


def check_provider_allowed(workspace_id: str, provider: str, plan: Optional[str] = None) -> bool:
    """Check whether the workspace's plan allows the given AI provider."""
    if plan is None:
        plan = get_workspace_plan(workspace_id)
    limits = get_plan_limits(plan)
    return provider in limits.ai_providers
