from datetime import datetime, timezone
from uuid import uuid4

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AnalysisRecord(db.Model):
    __tablename__ = "analysis_records"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    request_id = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="completed")

    requirements_text = db.Column(db.Text, nullable=False)
    ai_enhance_requested = db.Column(db.Boolean, nullable=False, server_default=db.text('FALSE'))
    ai_provider = db.Column(db.String(64), nullable=True)
    model = db.Column(db.String(128), nullable=True)
    intake_json = db.Column(db.Text, nullable=True)

    domain = db.Column(db.String(64), nullable=False)
    rms = db.Column(db.Integer, nullable=False)
    implied_users_json = db.Column(db.Text, nullable=False)
    missing_features_json = db.Column(db.Text, nullable=False)
    clarification_questions_json = db.Column(db.Text, nullable=False)
    conflicts_json = db.Column(db.Text, nullable=False)
    prd_json = db.Column(db.Text, nullable=False)
    ai_enhanced_json = db.Column(db.Text, nullable=True)
    answers_json = db.Column(db.Text, nullable=True)
    current_version_number = db.Column(db.Integer, nullable=False, default=1, server_default=db.text("1"))
    approved_version_number = db.Column(db.Integer, nullable=True)


class AnalysisVersion(db.Model):
    __tablename__ = "analysis_versions"
    __table_args__ = (
        db.UniqueConstraint("analysis_id", "version_number", name="uq_analysis_versions_analysis_id_version"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    analysis_id = db.Column(db.String(36), db.ForeignKey("analysis_records.id"), nullable=False, index=True)
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    product_brief_json = db.Column(db.Text, nullable=False)
    clarification_questions_json = db.Column(db.Text, nullable=False)
    prd_document_json = db.Column(db.Text, nullable=False)
    generation_run_json = db.Column(db.Text, nullable=False)
    legacy_prd_json = db.Column(db.Text, nullable=False)
    section_diffs_json = db.Column(db.Text, nullable=True)
    approval_state = db.Column(db.String(16), nullable=False, default="draft", server_default=db.text("'draft'"))
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)


class AnalysisJob(db.Model):
    __tablename__ = "analysis_jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    request_id = db.Column(db.String(64), nullable=True)
    analysis_id = db.Column(db.String(36), nullable=True)
    requirements_text = db.Column(db.Text, nullable=False)
    ai_enhance_requested = db.Column(db.Boolean, nullable=False, server_default=db.text('FALSE'))
    ai_provider = db.Column(db.String(64), nullable=True)
    model = db.Column(db.String(128), nullable=True)
    intake_json = db.Column(db.Text, nullable=True)
    quota_reservations_json = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(32), nullable=False, default="queued")
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=3)
    error_message = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)


class AuthSessionCredential(db.Model):
    __tablename__ = "auth_session_credentials"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False, default="owner")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    auth_session_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    provider = db.Column(db.String(32), nullable=False, default="session")
    encrypted_access_token = db.Column(db.Text, nullable=True)
    encrypted_refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)


class Workspace(db.Model):
    __tablename__ = "workspaces"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    name = db.Column(db.String(128), nullable=False)


class ExportRecord(db.Model):
    __tablename__ = "export_records"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    analysis_id = db.Column(db.String(36), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    export_format = db.Column(db.String(16), nullable=False)  # markdown, html, json
    content = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    content_length = db.Column(db.Integer, nullable=False, default=0)
    share_token = db.Column(db.String(64), nullable=True, unique=True, index=True)
    share_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    download_count = db.Column(db.Integer, nullable=False, default=0)


class ShareLink(db.Model):
    __tablename__ = "share_links"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    analysis_id = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    access_level = db.Column(db.String(16), nullable=False, default="view")  # view, edit
    created_by_role = db.Column(db.String(32), nullable=False, default="owner")
    view_count = db.Column(db.Integer, nullable=False, default=0)


class ProductEvent(db.Model):
    __tablename__ = "product_events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=True, index=True)
    analysis_id = db.Column(db.String(36), nullable=True, index=True)
    request_id = db.Column(db.String(64), nullable=True)

    category = db.Column(db.String(32), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    properties_json = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class QuotaUsage(db.Model):
    __tablename__ = "quota_usage"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    metric = db.Column(db.String(64), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False, default=1)
    used_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class QuotaReservation(db.Model):
    __tablename__ = "quota_reservations"
    __table_args__ = (
        db.UniqueConstraint("reservation_key", name="uq_quota_reservations_key"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, index=True)
    metric = db.Column(db.String(64), nullable=False, index=True)
    reservation_key = db.Column(db.String(64), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(16), nullable=False, default="reserved", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    released_at = db.Column(db.DateTime(timezone=True), nullable=True)


class WorkspaceSubscription(db.Model):
    __tablename__ = "workspace_subscriptions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    plan = db.Column(db.String(32), nullable=False, default="free")
    status = db.Column(db.String(16), nullable=False, default="active")  # active, past_due, canceled, expired
    provider = db.Column(db.String(32), nullable=True)  # e.g., "stripe"
    provider_subscription_id = db.Column(db.String(128), nullable=True)
    current_period_start = db.Column(db.DateTime(timezone=True), nullable=True)
    current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
    canceled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
