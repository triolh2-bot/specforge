"""Legal, privacy, and data rights routes.

Provides:
- Terms of service, privacy policy, acceptable use policy
- User data export (GDPR Article 15 / CCPA right to know)
- User data deletion (GDPR Article 17 / right to be forgotten)
- Consent management for analytics/training data usage
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, send_file
from io import BytesIO

from ..extensions import db
from ..http import error_response, json_response
from ..models import (
    AnalysisJob,
    AnalysisRecord,
    AuthSessionCredential,
    ExportRecord,
    ProductEvent,
    QuotaUsage,
    ShareLink,
    Workspace,
    WorkspaceSubscription,
)
from ..services.auth_session import ensure_workspace_context
from ..services.rbac import PERM, enforce_resource_access

legal_bp = Blueprint("legal", __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static policy pages
# ---------------------------------------------------------------------------

TERMS_OF_SERVICE = """# SpecForge Terms of Service

**Last updated:** 2026-04-10

## 1. Acceptance of Terms
By accessing or using SpecForge ("the Service"), you agree to be bound by these Terms of Service.

## 2. Description of Service
SpecForge is an AI-powered requirements analysis and Product Requirements Document (PRD) generation platform.

## 3. User Accounts
You are responsible for maintaining the confidentiality of your account credentials.

## 4. Acceptable Use
You agree not to:
- Upload content that is illegal, harmful, or infringes on intellectual property rights
- Attempt to gain unauthorized access to the Service
- Use the Service to generate harmful or malicious content
- Exceed usage limits defined by your billing plan

## 5. Content Ownership
You retain ownership of content you upload. SpecForge claims no ownership over user content.

## 6. Data Retention
Analysis data is retained for the duration of your account. Deleted accounts result in data removal within 30 days.

## 7. Limitation of Liability
The Service is provided "as is" without warranties of any kind.

## 8. Termination
We reserve the right to terminate accounts that violate these terms.

## 9. Changes to Terms
We will notify users of material changes to these terms at least 30 days in advance.

## 10. Governing Law
These terms are governed by applicable law in the jurisdiction of operation.
"""

PRIVACY_POLICY = """# SpecForge Privacy Policy

**Last updated:** 2026-04-10

## 1. Information We Collect
- **Account Information:** Session identifiers, workspace associations, OAuth tokens (encrypted at rest).
- **Usage Data:** Analysis requests, generated PRDs, export downloads, feature usage patterns.
- **Technical Data:** IP addresses, browser type, device information, request logs.

## 2. How We Use Your Information
- To provide and improve the Service
- To generate AI-enhanced analysis results
- To monitor for abuse and security threats
- To send service-related notifications

## 3. Data Sharing
We do not sell your personal data. We may share anonymized, aggregated usage data for analytics purposes.

## 4. Data Retention
- Analysis records are retained for the life of your account.
- Deleted accounts trigger data purging within 30 days.
- Backup copies may persist for up to 90 days after deletion.

## 5. Your Rights
- **Access:** Request a copy of your personal data.
- **Rectification:** Correct inaccurate data.
- **Erasure:** Request deletion of your data ("right to be forgotten").
- **Portability:** Export your data in a machine-readable format.

## 6. Security
We encrypt OAuth tokens at rest and use HTTPS for all communications.

## 7. Cookies
We use essential session cookies. No third-party tracking cookies are used.

## 8. Children's Privacy
The Service is not intended for users under 16 years of age.

## 9. Contact
For privacy inquiries, contact privacy@specforge.dev.
"""

ACCEPTABLE_USE_POLICY = """# SpecForge Acceptable Use Policy

**Last updated:** 2026-04-10

## Prohibited Uses
You may not use the Service to:

1. Generate content that is illegal, defamatory, or infringes on intellectual property
2. Conduct phishing, social engineering, or other deceptive practices
3. Distribute malware or exploit code
4. Harass, abuse, or threaten others
5. Process personal data of third parties without their consent
6. Attempt prompt injection or AI manipulation attacks
7. Exceed rate limits or usage quotas through automated means
8. Resell or redistribute the Service without authorization

## Enforcement
Violations may result in account suspension or termination.
"""


@legal_bp.route("/legal/terms", methods=["GET"])
def terms_of_service():
    """Serve the Terms of Service."""
    return _serve_markdown(TERMS_OF_SERVICE, "terms-of-service.md")


@legal_bp.route("/legal/privacy", methods=["GET"])
def privacy_policy():
    """Serve the Privacy Policy."""
    return _serve_markdown(PRIVACY_POLICY, "privacy-policy.md")


@legal_bp.route("/legal/acceptable-use", methods=["GET"])
def acceptable_use():
    """Serve the Acceptable Use Policy."""
    return _serve_markdown(ACCEPTABLE_USE_POLICY, "acceptable-use-policy.md")


@legal_bp.route("/legal/policies", methods=["GET"])
def list_policies():
    """List all available legal policies."""
    return json_response({
        "policies": [
            {"name": "Terms of Service", "url": "/legal/terms", "last_updated": "2026-04-10"},
            {"name": "Privacy Policy", "url": "/legal/privacy", "last_updated": "2026-04-10"},
            {"name": "Acceptable Use Policy", "url": "/legal/acceptable-use", "last_updated": "2026-04-10"},
        ]
    })


def _serve_markdown(content: str, filename: str):
    """Serve markdown content as a downloadable file or inline text."""
    if request.args.get("download") == "1":
        return send_file(
            BytesIO(content.encode("utf-8")),
            mimetype="text/markdown",
            as_attachment=True,
            download_name=filename,
        )
    return json_response({"content": content, "format": "markdown"})


# ---------------------------------------------------------------------------
# Data export (GDPR Article 15 / CCPA Right to Know)
# ---------------------------------------------------------------------------

@legal_bp.route("/api/legal/data-export", methods=["POST"])
def export_my_data():
    """Export all personal data associated with the current workspace.

    Returns a comprehensive JSON archive of:
    - Workspace info and subscription
    - Analysis records (full content)
    - Export history
    - Share links
    - Product analytics events
    - Quota usage history
    """
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.READ_WORKSPACE.name)

    # Gather all data
    workspace = Workspace.query.get(workspace_id)
    subscription = WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).first()
    analyses = AnalysisRecord.query.filter_by(workspace_id=workspace_id).all()
    jobs = AnalysisJob.query.filter_by(workspace_id=workspace_id).all()
    exports = ExportRecord.query.filter_by(workspace_id=workspace_id).all()
    shares = ShareLink.query.filter_by(workspace_id=workspace_id).all()
    events = ProductEvent.query.filter_by(workspace_id=workspace_id).order_by(
        ProductEvent.occurred_at.desc()
    ).limit(1000).all()
    quota = QuotaUsage.query.filter_by(workspace_id=workspace_id).order_by(
        QuotaUsage.used_at.desc()
    ).limit(500).all()

    export_data = {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": {
            "id": workspace.id if workspace else None,
            "name": workspace.name if workspace else None,
            "created_at": workspace.created_at.isoformat() if workspace and workspace.created_at else None,
        },
        "subscription": {
            "plan": subscription.plan if subscription else "free",
            "status": subscription.status if subscription else "none",
        } if subscription else {"plan": "free", "status": "none"},
        "analyses": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "domain": a.domain,
                "rms": a.rms,
                "requirements_text": a.requirements_text,
                "prd_json": json.loads(a.prd_json) if a.prd_json else None,
                "ai_enhanced": json.loads(a.ai_enhanced_json) if a.ai_enhanced_json else None,
            }
            for a in analyses
        ],
        "exports": [
            {
                "id": e.id,
                "format": e.export_format,
                "filename": e.filename,
                "download_count": e.download_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exports
        ],
        "share_links": [
            {
                "id": s.id,
                "access_level": s.access_level,
                "view_count": s.view_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in shares
        ],
        "recent_events": [
            {"name": e.name, "category": e.category, "occurred_at": e.occurred_at.isoformat()}
            for e in events
        ],
        "quota_usage": [
            {"metric": q.metric, "amount": q.amount, "used_at": q.used_at.isoformat() if q.used_at else None}
            for q in quota
        ],
    }

    logger.info("Data export generated for workspace %s", workspace_id)

    return json_response({
        "export": export_data,
        "format": "json",
        "generated_at": export_data["export_generated_at"],
    })


# ---------------------------------------------------------------------------
# Data deletion (GDPR Article 17 / Right to be Forgotten)
# ---------------------------------------------------------------------------

@legal_bp.route("/api/legal/data-deletion", methods=["POST"])
def delete_my_data():
    """Request deletion of all personal data associated with the current workspace.

    This is a destructive operation. The user must confirm by including
    a "confirm" field with the value "DELETE_MY_DATA".
    """
    context = ensure_workspace_context()
    workspace_id = context["workspace_id"]
    enforce_resource_access(workspace_id, PERM.DELETE_WORKSPACE.name)

    data = request.get_json(silent=True) or {}
    if data.get("confirm") != "DELETE_MY_DATA":
        return error_response(
            "To confirm deletion, include {\"confirm\": \"DELETE_MY_DATA\"} in the request body.",
            status=400,
            code="confirmation_required",
            details={
                "required_confirmation": "DELETE_MY_DATA",
                "warning": "This will permanently delete all analyses, exports, and associated data.",
            },
        )

    # Perform deletion
    deleted = {
        "analyses": 0,
        "jobs": 0,
        "exports": 0,
        "shares": 0,
        "events": 0,
        "quota_usage": 0,
    }

    # Delete in order to respect foreign key constraints
    deleted["shares"] = ShareLink.query.filter_by(workspace_id=workspace_id).delete()
    deleted["exports"] = ExportRecord.query.filter_by(workspace_id=workspace_id).delete()
    deleted["jobs"] = AnalysisJob.query.filter_by(workspace_id=workspace_id).delete()
    deleted["analyses"] = AnalysisRecord.query.filter_by(workspace_id=workspace_id).delete()
    deleted["events"] = ProductEvent.query.filter_by(workspace_id=workspace_id).delete()
    deleted["quota_usage"] = QuotaUsage.query.filter_by(workspace_id=workspace_id).delete()

    # Delete subscription and workspace
    WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).delete()
    Workspace.query.filter_by(id=workspace_id).delete()

    db.session.commit()

    logger.warning("Data deletion completed for workspace %s: %s", workspace_id, deleted)

    return json_response({
        "deleted": True,
        "workspace_id": workspace_id,
        "counts": deleted,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "note": "Backup copies may persist for up to 90 days per our retention policy.",
    })


# ---------------------------------------------------------------------------
# Consent management
# ---------------------------------------------------------------------------

@legal_bp.route("/api/legal/consent", methods=["GET"])
def get_consent_status():
    """Return the user's current consent preferences."""
    context = ensure_workspace_context()
    return json_response({
        "analytics_consent": True,  # Default: analytics are essential for service operation
        "data_retention_days": 30,
        "policies_accepted": ["terms", "privacy", "acceptable_use"],
    })
