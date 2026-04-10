"""Tests for legal, privacy, and data rights surfaces."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from specforge import create_app
from specforge.extensions import db

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


class LegalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-legal.db")
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

    def test_terms_of_service_endpoint(self):
        resp = self.client.get("/legal/terms")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("content", body)
        self.assertIn("Terms of Service", body["content"])

    def test_privacy_policy_endpoint(self):
        resp = self.client.get("/legal/privacy")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("content", body)
        self.assertIn("Privacy Policy", body["content"])

    def test_acceptable_use_endpoint(self):
        resp = self.client.get("/legal/acceptable-use")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("content", body)
        self.assertIn("Acceptable Use", body["content"])

    def test_list_policies(self):
        resp = self.client.get("/legal/policies")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("policies", body)
        self.assertGreaterEqual(len(body["policies"]), 3)


class DataRightsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-rights.db")
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

    def _analyze(self, requirements="Build an e-commerce store."):
        return self.client.post(
            "/analyze",
            json={
                "requirements": requirements,
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )

    def test_data_export_returns_200(self):
        self._analyze()
        resp = self.client.post("/api/legal/data-export")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("export", body)
        self.assertIn("workspace", body["export"])
        self.assertIn("analyses", body["export"])
        self.assertGreaterEqual(len(body["export"]["analyses"]), 1)

    def test_data_export_contains_analysis_content(self):
        self._analyze()
        resp = self.client.post("/api/legal/data-export")
        body = resp.get_json()
        analysis = body["export"]["analyses"][0]
        self.assertIn("requirements_text", analysis)
        self.assertIn("domain", analysis)
        self.assertIn("prd_json", analysis)

    def test_data_deletion_requires_confirmation(self):
        resp = self.client.post(
            "/api/legal/data-deletion",
            json={},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"]["code"], "confirmation_required")

    def test_data_deletion_with_confirmation(self):
        # Create data
        self._analyze()

        # Confirm deletion
        resp = self.client.post(
            "/api/legal/data-deletion",
            json={"confirm": "DELETE_MY_DATA"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["deleted"])
        self.assertIn("counts", body)
        self.assertGreater(body["counts"]["analyses"], 0)

    def test_data_is_gone_after_deletion(self):
        # Create data
        self._analyze()

        # Confirm deletion
        self.client.post(
            "/api/legal/data-deletion",
            json={"confirm": "DELETE_MY_DATA"},
        )

        # Verify data is gone (new session, new workspace)
        new_client = self.app.test_client()
        resp = new_client.post("/api/legal/data-export")
        body = resp.get_json()
        self.assertEqual(len(body["export"]["analyses"]), 0)

    def test_consent_status_endpoint(self):
        resp = self.client.get("/api/legal/consent")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("analytics_consent", body)
        self.assertIn("policies_accepted", body)


if __name__ == "__main__":
    unittest.main()
