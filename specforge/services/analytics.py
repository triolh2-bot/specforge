"""Product analytics — funnel tracking, event logging, and usage instrumentation.

Unlike the operational metrics in ``observability`` (latency, error rates, queue
depth), this module tracks *user behaviour*: sign-ups, first analyses, exports,
provider usage, repeat sessions, and drop-off points.

Events are persisted in the database via the ``ProductEvent`` model so they
survive restarts and can be queried for dashboards and BI.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..extensions import db
from ..models import ProductEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

class EventCategory(str):
    """Top-level event categories."""
    AUTH = "auth"
    ANALYSIS = "analysis"
    EXPORT = "export"
    SHARING = "sharing"
    PROVIDER = "provider"
    WORKSPACE = "workspace"
    SESSION = "session"


class EventName(str):
    """Canonical event names tracked by the product."""
    # Auth funnel
    AUTH_SESSION_STARTED = "auth.session_started"
    AUTH_WORKSPACE_CREATED = "auth.workspace_created"
    AUTH_OAUTH_INITIATED = "auth.oauth_initiated"
    AUTH_OAUTH_COMPLETED = "auth.oauth_completed"
    AUTH_LOGOUT = "auth.logout"

    # Analysis funnel
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    ANALYSIS_VIEWED = "analysis.viewed"
    ANALYSIS_DELETED = "analysis.deleted"
    ANALYSIS_RERUN = "analysis.rerun"

    # Export funnel
    EXPORT_STARTED = "export.started"
    EXPORT_COMPLETED = "export.completed"
    EXPORT_DOWNLOADED = "export.downloaded"
    EXPORT_SHARED = "export.shared"

    # Sharing
    SHARE_LINK_CREATED = "share.link_created"
    SHARE_LINK_VIEWED = "share.link_viewed"
    SHARE_LINK_EXPIRED = "share.link_expired"

    # Provider usage
    PROVIDER_SELECTED = "provider.selected"
    PROVIDER_ENHANCEMENT_SUCCESS = "provider.enhancement_success"
    PROVIDER_ENHANCEMENT_FAILED = "provider.enhancement_failed"
    PROVIDER_FALLBACK = "provider.fallback"

    # Workspace
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_MEMBER_ADDED = "workspace.member_added"
    WORKSPACE_MEMBER_REMOVED = "workspace.member_removed"
    WORKSPACE_ROLE_CHANGED = "workspace.role_changed"

    # Session
    SESSION_FIRST_ANALYSIS = "session.first_analysis"
    SESSION_RETURNING = "session.returning"


# ---------------------------------------------------------------------------
# Tracking functions
# ---------------------------------------------------------------------------

def track_event(
    name: str,
    category: str = "",
    workspace_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Optional[ProductEvent]:
    """Record a product event in the database.

    Returns the created event record, or ``None`` if tracking is unavailable.
    """
    try:
        event = ProductEvent(
            workspace_id=workspace_id,
            analysis_id=analysis_id,
            request_id=request_id,
            category=category or name.split(".")[0],
            name=name,
            properties_json=json.dumps(properties or {}, default=str),
            occurred_at=datetime.now(timezone.utc),
        )
        db.session.add(event)
        db.session.commit()
        return event
    except Exception:
        logger.debug("Failed to persist analytics event '%s'", name, exc_info=True)
        db.session.rollback()
        return None


def track_funnel_event(
    name: str,
    workspace_id: Optional[str],
    analysis_id: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Optional[ProductEvent]:
    """Record a funnel event and log it structurally."""
    event = track_event(name, workspace_id=workspace_id, analysis_id=analysis_id, properties=properties, request_id=request_id)
    if event:
        logger.info(
            "product_event",
            extra={
                "event": "product_analytics",
                "event_name": name,
                "workspace_id": workspace_id,
                "analysis_id": analysis_id,
                "request_id": request_id,
            },
        )
    return event


# ---------------------------------------------------------------------------
# High-level tracking helpers
# ---------------------------------------------------------------------------

def track_analysis_started(workspace_id: str, ai_provider: str, use_ai: bool, request_id: Optional[str] = None):
    track_funnel_event(
        EventName.ANALYSIS_STARTED,
        workspace_id=workspace_id,
        properties={"ai_provider": ai_provider, "use_ai": use_ai},
        request_id=request_id,
    )


def track_analysis_completed(
    workspace_id: str,
    analysis_id: str,
    domain: str,
    rms: int,
    ai_provider: str,
    ai_enhanced: bool,
    request_id: Optional[str] = None,
):
    track_funnel_event(
        EventName.ANALYSIS_COMPLETED,
        workspace_id=workspace_id,
        analysis_id=analysis_id,
        properties={"domain": domain, "rms": rms, "ai_provider": ai_provider, "ai_enhanced": ai_enhanced},
        request_id=request_id,
    )


def track_analysis_failed(workspace_id: str, error: str, request_id: Optional[str] = None):
    track_funnel_event(
        EventName.ANALYSIS_FAILED,
        workspace_id=workspace_id,
        properties={"error": error},
        request_id=request_id,
    )


def track_export_completed(workspace_id: str, export_format: str, analysis_id: Optional[str] = None, request_id: Optional[str] = None):
    track_funnel_event(
        EventName.EXPORT_COMPLETED,
        workspace_id=workspace_id,
        analysis_id=analysis_id,
        properties={"export_format": export_format},
        request_id=request_id,
    )


def track_provider_selected(workspace_id: str, provider: str, request_id: Optional[str] = None):
    track_funnel_event(
        EventName.PROVIDER_SELECTED,
        workspace_id=workspace_id,
        properties={"provider": provider},
        request_id=request_id,
    )


def track_session_event(workspace_id: str, is_first_analysis: bool, request_id: Optional[str] = None):
    if is_first_analysis:
        track_funnel_event(EventName.SESSION_FIRST_ANALYSIS, workspace_id=workspace_id, request_id=request_id)
    else:
        track_funnel_event(EventName.SESSION_RETURNING, workspace_id=workspace_id, request_id=request_id)


# ---------------------------------------------------------------------------
# Analytics queries (for dashboards and admin views)
# ---------------------------------------------------------------------------

def get_funnel_summary(workspace_id: Optional[str] = None, days: int = 30) -> dict[str, Any]:
    """Return funnel counts for the last *days* days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = ProductEvent.query
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)
    query = query.filter(ProductEvent.occurred_at >= since)

    events = query.all()

    funnel = {
        "sessions": 0,
        "analyses_started": 0,
        "analyses_completed": 0,
        "analyses_with_ai": 0,
        "exports": 0,
        "exports_downloaded": 0,
        "shares_created": 0,
    }

    for ev in events:
        props = json.loads(ev.properties_json) if ev.properties_json else {}
        if ev.name == EventName.SESSION_FIRST_ANALYSIS:
            funnel["sessions"] += 1
        elif ev.name == EventName.ANALYSIS_STARTED:
            funnel["analyses_started"] += 1
        elif ev.name == EventName.ANALYSIS_COMPLETED:
            funnel["analyses_completed"] += 1
            if props.get("ai_enhanced"):
                funnel["analyses_with_ai"] += 1
        elif ev.name == EventName.EXPORT_COMPLETED:
            funnel["exports"] += 1
        elif ev.name == EventName.EXPORT_DOWNLOADED:
            funnel["exports_downloaded"] += 1
        elif ev.name == EventName.SHARE_LINK_CREATED:
            funnel["shares_created"] += 1

    return funnel


def get_domain_distribution(workspace_id: Optional[str] = None, days: int = 30) -> dict[str, int]:
    """Return analysis count by detected domain."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = ProductEvent.query.filter_by(name=EventName.ANALYSIS_COMPLETED)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)
    query = query.filter(ProductEvent.occurred_at >= since)

    distribution: dict[str, int] = {}
    for ev in query.all():
        props = json.loads(ev.properties_json) if ev.properties_json else {}
        domain = props.get("domain", "unknown")
        distribution[domain] = distribution.get(domain, 0) + 1
    return distribution


def get_provider_usage(workspace_id: Optional[str] = None, days: int = 30) -> dict[str, Any]:
    """Return provider usage statistics."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = ProductEvent.query.filter(ProductEvent.occurred_at >= since)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    events = query.filter(
        ProductEvent.name.in_([
            EventName.PROVIDER_SELECTED,
            EventName.PROVIDER_ENHANCEMENT_SUCCESS,
            EventName.PROVIDER_ENHANCEMENT_FAILED,
        ])
    ).all()

    providers: dict[str, dict[str, int]] = {}
    for ev in events:
        props = json.loads(ev.properties_json) if ev.properties_json else {}
        provider = props.get("provider", "unknown")
        if provider not in providers:
            providers[provider] = {"selected": 0, "success": 0, "failed": 0}

        if ev.name == EventName.PROVIDER_SELECTED:
            providers[provider]["selected"] += 1
        elif ev.name == EventName.PROVIDER_ENHANCEMENT_SUCCESS:
            providers[provider]["success"] += 1
        elif ev.name == EventName.PROVIDER_ENHANCEMENT_FAILED:
            providers[provider]["failed"] += 1

    return providers


def get_usage_over_time(workspace_id: Optional[str] = None, days: int = 30) -> list[dict[str, Any]]:
    """Return daily usage counts (analyses, exports) over the last *days* days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = ProductEvent.query.filter(ProductEvent.occurred_at >= since)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    events = query.all()
    daily: dict[str, dict[str, int]] = {}

    for ev in events:
        day_key = ev.occurred_at.strftime("%Y-%m-%d")
        if day_key not in daily:
            daily[day_key] = {"analyses": 0, "exports": 0, "sessions": 0}

        if "analysis" in ev.name:
            daily[day_key]["analyses"] += 1
        elif "export" in ev.name:
            daily[day_key]["exports"] += 1
        elif "session" in ev.name:
            daily[day_key]["sessions"] += 1

    return sorted(
        [{"date": k, **v} for k, v in daily.items()],
        key=lambda x: x["date"],
    )
