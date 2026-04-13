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
    OPENROUTER_API_KEY = ""
    OPENROUTER_MODEL = "openai/gpt-4o-mini"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 256
    RATE_LIMITS = {
        "analyze": {"limit": 2, "window": 60},
        "ai_chat": {"limit": 2, "window": 60},
        "ai_enhance": {"limit": 2, "window": 60},
        "auth_login": {"limit": 2, "window": 60},
        "auth_callback": {"limit": 2, "window": 60},
        "list_analyses": {"limit": 2, "window": 60},
        "get_analysis": {"limit": 2, "window": 60},
        "get_job": {"limit": 2, "window": 60},
        "auth_status": {"limit": 2, "window": 60},
    }


class AbuseProtectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-abuse.db")
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

    def test_analyze_rate_limit_returns_429(self):
        payload = {
            "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
            "ai_enhance": False,
                "ai_provider": "openrouter",
        }
        first = self.client.post("/analyze", json=payload)
        second = self.client.post("/analyze", json=payload)
        third = self.client.post("/analyze", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.get_json()["error"]["code"], "rate_limit_exceeded")
        self.assertIn("Retry-After", third.headers)

    def test_payload_too_large_returns_413(self):
        oversized = "x" * 400
        response = self.client.post(
            "/analyze",
            data=f'{{"requirements":"{oversized}","ai_enhance":false,"ai_provider":"openrouter"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"]["code"], "payload_too_large")

    def test_auth_status_rate_limit_isolated_by_session(self):
        other_client = self.app.test_client()
        self.assertEqual(self.client.get("/auth/status").status_code, 200)
        self.assertEqual(self.client.get("/auth/status").status_code, 200)
        limited = self.client.get("/auth/status")
        fresh = other_client.get("/auth/status")

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(fresh.status_code, 200)


if __name__ == "__main__":
    unittest.main()
