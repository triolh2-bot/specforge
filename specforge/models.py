from datetime import datetime, timezone
from uuid import uuid4

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AnalysisRecord(db.Model):
    __tablename__ = "analysis_records"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    request_id = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="completed")

    requirements_text = db.Column(db.Text, nullable=False)
    ai_enhance_requested = db.Column(db.Boolean, nullable=False, default=False)
    ai_provider = db.Column(db.String(64), nullable=True)

    domain = db.Column(db.String(64), nullable=False)
    rms = db.Column(db.Integer, nullable=False)
    implied_users_json = db.Column(db.Text, nullable=False)
    missing_features_json = db.Column(db.Text, nullable=False)
    clarification_questions_json = db.Column(db.Text, nullable=False)
    conflicts_json = db.Column(db.Text, nullable=False)
    prd_json = db.Column(db.Text, nullable=False)
    ai_enhanced_json = db.Column(db.Text, nullable=True)


class AnalysisJob(db.Model):
    __tablename__ = "analysis_jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    request_id = db.Column(db.String(64), nullable=True)
    analysis_id = db.Column(db.String(36), nullable=True)
    requirements_text = db.Column(db.Text, nullable=False)
    ai_enhance_requested = db.Column(db.Boolean, nullable=False, default=False)
    ai_provider = db.Column(db.String(64), nullable=True)

    status = db.Column(db.String(32), nullable=False, default="queued")
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=3)
    error_message = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)
