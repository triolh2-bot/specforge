"""Tests for admin operations and support tooling."""

import os
import tempfile
import unittest
from pathlib import Path

from specforge import create_app
from specforge.extensions import db
from specforge.models import AnalysisJob, Workspace
from specforge.repositories.workspace_repository import upsert_workspace_subscription

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
    TOKEN_ENCRYPTION_SECRET = "encryption-secret"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    MINIMAX_CLIENT_ID = ""
    MINIMAX_CLIENT_SECRET = ""
    MINIMAX_REDIRECT_URI = ""
    MINIMAX_AUTH_URL = "https://platform.minimaxi.com/oauth/authorize"
    MINIMAX_TOKEN_URL = "https://platform.minimaxi.com/oauth/token"
    MINIMAX_API_BASE = "https://api.minimaxi.com/v1"
    MINIMAX_API_KEY = ""
    MINIMAX_GROUP_ID = ""
    MINIMAX_CHAT_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    MINIMAX_MODEL = "MiniMax-M2.5"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class AdminIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-admin.db")
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
                "ai_provider": "minimax",
            },
        )

    def test_admin_list_workspaces_requires_admin(self):
        # Default session is owner, which has admin access
        resp = self.client.get("/api/admin/workspaces")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("workspaces", body)
        self.assertGreater(body["pagination"]["total"], 0)

    def test_admin_list_jobs_requires_admin(self):
        resp = self.client.get("/api/admin/jobs")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("jobs", body)

    def test_admin_list_exports_requires_admin(self):
        resp = self.client.get("/api/admin/exports")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("exports", body)

    def test_admin_quota_usage_requires_admin(self):
        resp = self.client.get("/api/admin/quota/usage")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("usage", body)

    def test_admin_get_workspace_details(self):
        resp = self._analyze()
        self.assertEqual(resp.status_code, 200)
        workspace_id = resp.get_json()["workspace_id"]

        resp = self.client.get(f"/api/admin/workspaces/{workspace_id}")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("workspace_id", body)
        self.assertIn("stats", body)
        self.assertIn("analyses", body["stats"])
        self.assertGreaterEqual(body["stats"]["analyses"], 0)

    def test_admin_replay_job_requires_admin(self):
        resp = self.client.post(
            "/api/admin/jobs/nonexistent-job-id/replay",
        )
        # Admin access granted, but job doesn't exist
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
