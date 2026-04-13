import os
import unittest
from pathlib import Path
from unittest.mock import patch

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
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QUOTA_ENFORCEMENT = "off"
    OPENROUTER_API_KEY = ""
    OPENROUTER_MODEL = "openai/gpt-4o-mini"


class BriefRouteTests(unittest.TestCase):
    def setUp(self):
        tmp_dir = REPO_ROOT / "tests" / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        self.db_path = tmp_dir / "specforge-brief-route.db"
        if self.db_path.exists():
            self.db_path.unlink()
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.client = self.app.test_client()
        self.same_origin_headers = {
            "Origin": "http://localhost",
            "Referer": "http://localhost/",
        }

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def _payload(self):
        return {
            "project_name": "PlanPlate",
            "project_type": "Web Application",
            "core_idea": "Help families plan meals, share grocery lists, and track weekly dinner plans.",
            "target_audience": "Busy households",
            "key_features": "Meal calendar, grocery list, shared household access",
            "ai_provider": "openrouter",
        }

    def test_brief_route_maps_rate_limits_to_429(self):
        with patch("specforge.routes.main.generate_brief", return_value={
            "success": False,
            "error": "429 Client Error: Too Many Requests for url: https://openrouter.ai/api/v1/chat/completions",
        }):
            resp = self.client.post(
                "/api/generate-brief",
                json=self._payload(),
                headers=self.same_origin_headers,
            )

        self.assertEqual(resp.status_code, 429)
        body = resp.get_json()
        self.assertEqual(body["error"]["code"], "provider_rate_limited")

    def test_brief_route_maps_provider_errors_to_502(self):
        with patch("specforge.routes.main.generate_brief", return_value={
            "success": False,
            "error": "OpenRouter API key not configured",
        }):
            resp = self.client.post(
                "/api/generate-brief",
                json=self._payload(),
                headers=self.same_origin_headers,
            )

        self.assertEqual(resp.status_code, 502)
        body = resp.get_json()
        self.assertEqual(body["error"]["code"], "provider_error")

    def test_brief_route_keeps_validation_failures_as_400(self):
        with patch("specforge.routes.main.generate_brief", return_value={
            "success": False,
            "error": "Core idea must be at least 10 characters.",
        }):
            resp = self.client.post(
                "/api/generate-brief",
                json=self._payload(),
                headers=self.same_origin_headers,
            )

        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body["error"]["code"], "validation_error")


if __name__ == "__main__":
    unittest.main()
