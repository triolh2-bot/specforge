import os
import tempfile
import unittest
from unittest.mock import patch

from specforge import create_app
from specforge.extensions import db


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
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
    HEALTH_QUEUE_BACKLOG_WARNING = 1
    HEALTH_QUEUE_BACKLOG_CRITICAL = 2
    HEALTH_FAILED_JOBS_CRITICAL = 1


class HealthCheckTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-health.db")
        migrations_dir = os.path.join("/home/kali/.openclaw/workspace/specforge-mvp", "migrations")

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

    def test_liveness_endpoint_reports_uptime(self):
        response = self.client.get("/health/live")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "alive")
        self.assertIn("uptime_seconds", body)
        self.assertGreaterEqual(body["uptime_seconds"], 0)

    def test_readiness_endpoint_reports_dependency_checks(self):
        response = self.client.get("/health/ready")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["ready"])
        self.assertEqual(body["summary"]["database"], "ok")
        self.assertEqual(body["summary"]["migrations"], "ok")
        self.assertEqual(body["summary"]["queue"], "ok")

    def test_readiness_warns_for_backlog_without_failing(self):
        self.client.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": True,
                "ai_provider": "minimax",
            },
        )

        response = self.client.get("/health/ready")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["summary"]["queue"], "degraded")
        self.assertTrue(body["ready"])

    def test_readiness_fails_for_database_outage(self):
        with patch("specforge.services.health.check_database", return_value={"name": "database", "status": "down", "required": True}):
            response = self.client.get("/health/ready")
            body = response.get_json()

        self.assertEqual(response.status_code, 503)
        self.assertFalse(body["ready"])
        self.assertEqual(body["summary"]["database"], "down")

    def test_health_endpoint_remains_compatibility_alias(self):
        response = self.client.get("/health")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["endpoint"], "/health")
        self.assertEqual(body["mode"], "compatibility")


if __name__ == "__main__":
    unittest.main()
