"""Tests for product analytics and instrumentation."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from specforge import create_app
from specforge.extensions import db
from specforge.services.analytics import (
    EventName,
    get_domain_distribution,
    get_funnel_summary,
    get_provider_usage,
    get_usage_over_time,
    track_event,
    track_funnel_event,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
    TOKEN_ENCRYPTION_SECRET = "encryption-secret"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    OPENROUTER_API_KEY = ""
    OPENROUTER_MODEL = "openai/gpt-4o-mini"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestAnalyticsTracking(unittest.TestCase):
    """Unit tests for the analytics tracking functions."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-analytics.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_track_event_persists_to_db(self):
        with self.app.app_context():
            event = track_event(
                name="test.event",
                category="test",
                workspace_id="ws-123",
                analysis_id="an-456",
                properties={"key": "value"},
            )
            self.assertIsNotNone(event)
            self.assertEqual(event.name, "test.event")
            self.assertEqual(event.workspace_id, "ws-123")
            props = json.loads(event.properties_json)
            self.assertEqual(props["key"], "value")

    def test_track_funnel_event_logs(self):
        with self.app.app_context():
            event = track_funnel_event(
                EventName.ANALYSIS_STARTED,
                workspace_id="ws-123",
                properties={"ai_provider": "openrouter", "use_ai": True},
            )
            self.assertIsNotNone(event)
            self.assertEqual(event.name, EventName.ANALYSIS_STARTED)
            props = json.loads(event.properties_json)
            self.assertEqual(props["ai_provider"], "openrouter")


class AnalyticsIntegrationTests(unittest.TestCase):
    """Integration tests for analytics endpoints."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-analytics.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def _analyze(self, requirements="Build an e-commerce store with cart and checkout."):
        return self.client.post(
            "/analyze",
            json={
                "requirements": requirements,
                "ai_enhance": False,
                "ai_provider": "openrouter",
            },
        )

    def test_analyze_tracks_event(self):
        self._analyze()
        with self.app.app_context():
            summary = get_funnel_summary(days=1)
            self.assertGreater(summary["analyses_started"], 0)
            self.assertGreater(summary["analyses_completed"], 0)

    def test_funnel_endpoint_returns_200(self):
        self._analyze()
        resp = self.client.get("/api/analytics/funnel")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("funnel", body)
        self.assertIn("analyses_started", body["funnel"])
        self.assertIn("analyses_completed", body["funnel"])

    def test_domains_endpoint_returns_distribution(self):
        self._analyze()
        self._analyze("Build a SaaS platform with subscription billing.")
        resp = self.client.get("/api/analytics/domains")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("domains", body)
        self.assertIn("e-commerce", body["domains"])
        self.assertIn("saas", body["domains"])

    def test_providers_endpoint_returns_usage(self):
        self._analyze()
        resp = self.client.get("/api/analytics/providers")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("providers", body)

    def test_trends_endpoint_returns_daily_data(self):
        self._analyze()
        resp = self.client.get("/api/analytics/trends")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("trends", body)
        self.assertIsInstance(body["trends"], list)

    def test_export_tracks_event(self):
        # Create analysis
        resp = self._analyze()
        analysis_id = resp.get_json()["analysis_id"]

        # Create export
        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": analysis_id, "format": "markdown"},
        )
        self.assertEqual(resp.status_code, 201)

        with self.app.app_context():
            funnel = get_funnel_summary(days=1)
            self.assertGreater(funnel["exports"], 0)


if __name__ == "__main__":
    unittest.main()
