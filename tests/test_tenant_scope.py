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


class TenantScopeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-tenant.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client_a = self.app.test_client()
        self.client_b = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_analysis_is_scoped_to_current_workspace(self):
        response = self.client_a.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )
        analysis_id = response.get_json()["analysis_id"]

        allowed = self.client_a.get(f"/api/analyses/{analysis_id}")
        denied = self.client_b.get(f"/api/analyses/{analysis_id}")

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(denied.status_code, 404)

    def test_job_is_scoped_to_current_workspace(self):
        response = self.client_a.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": True,
                "ai_provider": "minimax",
            },
        )
        job_id = response.get_json()["job_id"]

        allowed = self.client_a.get(f"/api/jobs/{job_id}")
        denied = self.client_b.get(f"/api/jobs/{job_id}")

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(denied.status_code, 404)

    def test_analysis_history_only_lists_current_workspace_records(self):
        self.client_a.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )
        self.client_b.post(
            "/analyze",
            json={
                "requirements": "I need a CRM for lead tracking and a sales dashboard.",
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )

        history_a = self.client_a.get("/api/analyses")
        history_b = self.client_b.get("/api/analyses")

        self.assertEqual(history_a.status_code, 200)
        self.assertEqual(history_b.status_code, 200)
        self.assertEqual(history_a.get_json()["pagination"]["total"], 1)
        self.assertEqual(history_b.get_json()["pagination"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
