"""Export and share routes."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, Response

from ..extensions import db
from ..http import error_response, json_response
from ..models import ExportRecord, ShareLink
from ..services.abuse import rate_limit
from ..services.analysis_store import fetch_analysis
from ..services.analytics import track_export_completed, track_funnel_event, EventName
from ..services.auth_session import ensure_workspace_context
from ..services.billing import consume_quota, QuotaExceededError
from ..services.exports import generate_export, SUPPORTED_FORMATS
from ..services.rbac import PERM, enforce_resource_access, require_permission

exports_bp = Blueprint("exports", __name__)


def _get_analysis_or_404(analysis_id: str, workspace_id: str) -> dict:
    """Fetch an analysis or return 404."""
    analysis = fetch_analysis(analysis_id, workspace_id)
    if not analysis:
        return None
    return analysis


def _generate_share_token() -> str:
    return secrets.token_urlsafe(32)


@exports_bp.route("/api/exports", methods=["POST"])
@rate_limit("minimax_chat")
def create_export():
    """Create a new export for an analysis."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    data = request.get_json(silent=True) or {}
    analysis_id = data.get("analysis_id")
    export_format = data.get("format", "markdown").lower()

    if not analysis_id:
        return error_response("analysis_id is required", status=400, code="missing_analysis_id")

    if export_format not in SUPPORTED_FORMATS:
        return error_response(
            f"Unsupported format '{export_format}'. Supported: {', '.join(SUPPORTED_FORMATS)}",
            status=400,
            code="unsupported_format",
            details={"supported_formats": SUPPORTED_FORMATS},
        )

    enforce_resource_access(workspace_id, PERM.WRITE_EXPORTS.name)

    analysis = _get_analysis_or_404(analysis_id, workspace_id)
    if not analysis:
        return error_response("Analysis not found", status=404, code="analysis_not_found")

    # Check and consume export quota
    try:
        consume_quota(workspace_id, "export")
    except QuotaExceededError as exc:
        return json_response(
            {
                "success": False,
                "error": {
                    "code": "quota_exceeded",
                    "message": str(exc),
                    "metric": exc.metric,
                    "limit": exc.limit,
                    "plan": exc.plan,
                },
            },
            status=429,
        )

    try:
        content, filename = generate_export(analysis, export_format)
    except Exception as exc:
        return error_response(f"Export generation failed: {exc}", status=500, code="export_failed")

    share_token = _generate_share_token()
    share_expires = datetime.now(timezone.utc) + timedelta(days=7)

    record = ExportRecord(
        workspace_id=workspace_id,
        analysis_id=analysis_id,
        export_format=export_format,
        content=content,
        filename=filename,
        content_length=len(content),
        share_token=share_token,
        share_expires_at=share_expires,
    )
    db.session.add(record)
    db.session.commit()

    track_export_completed(
        workspace_id=workspace_id,
        export_format=export_format,
        analysis_id=analysis_id,
        request_id=None,
    )

    return json_response({
        "export_id": record.id,
        "format": export_format,
        "filename": filename,
        "content_length": record.content_length,
        "share_url": f"/api/exports/share/{share_token}",
        "share_expires_at": share_expires.isoformat(),
        "created_at": record.created_at.isoformat(),
    }, status=201)


@exports_bp.route("/api/exports", methods=["GET"])
@require_permission(PERM.READ_EXPORTS.name)
def list_exports():
    """List recent exports for the current workspace."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    limit = min(request.args.get("limit", 20, type=int), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)

    query = ExportRecord.query.filter_by(workspace_id=workspace_id)
    total = query.count()
    records = query.order_by(ExportRecord.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for r in records:
        items.append({
            "export_id": r.id,
            "analysis_id": r.analysis_id,
            "format": r.export_format,
            "filename": r.filename,
            "content_length": r.content_length,
            "download_count": r.download_count,
            "share_url": f"/api/exports/share/{r.share_token}" if r.share_token else None,
            "created_at": r.created_at.isoformat(),
        })

    return json_response({
        "items": items,
        "pagination": {"limit": limit, "offset": offset, "total": total},
    })


@exports_bp.route("/api/exports/<export_id>/download", methods=["GET"])
@rate_limit("get_analysis")
def download_export(export_id: str):
    """Download an export file."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    record = ExportRecord.query.filter_by(id=export_id, workspace_id=workspace_id).first()
    if not record:
        return error_response("Export not found", status=404, code="export_not_found")

    # Increment download count
    record.download_count += 1
    db.session.commit()

    # Serve the file
    mime_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json",
    }
    return Response(
        record.content,
        mimetype=mime_types.get(record.export_format, "text/plain"),
        headers={
            "Content-Disposition": f"attachment; filename={record.filename}",
        },
    )


@exports_bp.route("/api/exports/share/<token>", methods=["GET"])
def get_shared_export(token: str):
    """Access an export via share token (no auth required)."""
    record = ExportRecord.query.filter_by(share_token=token).first()
    if not record:
        return error_response("Shared export not found", status=404, code="share_not_found")

    # Check expiration
    if record.share_expires_at:
        expires_at = record.share_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return error_response("Share link has expired", status=410, code="share_expired")

    # Increment view count
    record.download_count += 1
    db.session.commit()

    mime_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json",
    }
    return Response(
        record.content,
        mimetype=mime_types.get(record.export_format, "text/plain"),
        headers={
            "Content-Disposition": f"attachment; filename={record.filename}",
        },
    )


@exports_bp.route("/api/analyses/<analysis_id>/share", methods=["POST"])
@require_permission(PERM.WRITE_EXPORTS.name)
def create_share_link(analysis_id: str):
    """Create a shareable link for an analysis (view-only PRD page)."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    analysis = _get_analysis_or_404(analysis_id, workspace_id)
    if not analysis:
        return error_response("Analysis not found", status=404, code="analysis_not_found")

    data = request.get_json(silent=True) or {}
    expires_days = min(data.get("expires_days", 7), 30)
    access_level = data.get("access_level", "view")

    if access_level not in ("view", "edit"):
        return error_response("access_level must be 'view' or 'edit'", status=400, code="invalid_access_level")

    token = _generate_share_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

    link = ShareLink(
        workspace_id=workspace_id,
        analysis_id=analysis_id,
        token=token,
        access_level=access_level,
        expires_at=expires_at,
        created_by_role=context.get("role", "owner"),
    )
    db.session.add(link)
    db.session.commit()

    track_funnel_event(
        EventName.SHARE_LINK_CREATED,
        workspace_id=workspace_id,
        analysis_id=analysis_id,
        properties={"access_level": access_level, "expires_days": expires_days},
        request_id=None,
    )

    return json_response({
        "share_id": link.id,
        "share_url": f"/shared/{token}",
        "access_level": access_level,
        "expires_at": expires_at.isoformat(),
        "created_at": link.created_at.isoformat(),
    }, status=201)


@exports_bp.route("/api/analyses/<analysis_id>/shares", methods=["GET"])
@require_permission(PERM.READ_EXPORTS.name)
def list_share_links(analysis_id: str):
    """List share links for an analysis."""
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]

    # Verify analysis belongs to workspace
    analysis = _get_analysis_or_404(analysis_id, workspace_id)
    if not analysis:
        return error_response("Analysis not found", status=404, code="analysis_not_found")

    links = ShareLink.query.filter_by(
        workspace_id=workspace_id,
        analysis_id=analysis_id,
    ).order_by(ShareLink.created_at.desc()).all()

    items = []
    now = datetime.now(timezone.utc)
    for link in links:
        expires_at = link.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        is_expired = expires_at is not None and expires_at < now

        link_expires_str = None
        if link.expires_at:
            if link.expires_at.tzinfo is None:
                link_expires_str = link.expires_at.replace(tzinfo=timezone.utc).isoformat()
            else:
                link_expires_str = link.expires_at.isoformat()

        items.append({
            "share_id": link.id,
            "share_url": f"/shared/{link.token}",
            "access_level": link.access_level,
            "expires_at": link_expires_str,
            "is_expired": is_expired,
            "view_count": link.view_count,
            "created_at": link.created_at.isoformat(),
        })

    return json_response({"items": items, "count": len(items)})
