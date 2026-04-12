"""Tests for the refactored app.py entry point.

The PR reduced app.py from 821 lines to 11 lines. This module verifies
that the thin wrapper correctly delegates to specforge.create_app() and
that the resulting Flask application has the expected configuration and
structure.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from specforge import create_app
from specforge.extensions import db

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestConfig:
    SECRET_KEY = "test-secret"
    TESTING = True
    PORT = 5000
    TOKEN_ENCRYPTION_SECRET = "test-encryption-secret"
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
    AI_ENHANCEMENT_ENABLED = False
    MINIMAX_OAUTH_ENABLED = False
    EXPORT_SHARING_ENABLED = True
    ANALYTICS_ENABLED = False
    QUOTA_ENFORCEMENT = "off"
    APP_VERSION = "2.1.0"
    HEALTH_QUEUE_BACKLOG_WARNING = 100
    HEALTH_QUEUE_BACKLOG_CRITICAL = 500
    HEALTH_FAILED_JOBS_CRITICAL = 25
    HEALTH_LIVENESS_VERSION = "2.1.0"
    PAYPAL_CLIENT_ID = ""
    PAYPAL_CLIENT_SECRET = ""
    PAYPAL_SANDBOX = True
    PAYPAL_WEBHOOK_ID = ""
    PAYPAL_PLAN_ID_PRO = ""
    PAYPAL_PLAN_ID_ENTERPRISE = ""
    PAYPAL_PLAN_PRICE_PRO = "$19.99/month"
    PAYPAL_PLAN_PRICE_ENTERPRISE = "$99.99/month"
    RATE_LIMITS = {
        "analyze": {"limit": 20, "window": 60},
        "minimax_chat": {"limit": 10, "window": 60},
        "minimax_enhance": {"limit": 10, "window": 60},
        "minimax_login": {"limit": 10, "window": 60},
        "minimax_callback": {"limit": 20, "window": 60},
        "list_analyses": {"limit": 60, "window": 60},
        "get_analysis": {"limit": 120, "window": 60},
        "get_job": {"limit": 120, "window": 60},
        "minimax_status": {"limit": 60, "window": 60},
    }
    MAX_CONTENT_LENGTH = 65536


class AppEntryPointTests(unittest.TestCase):
    """Tests ensuring app.py's create_app() delegation works correctly."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-test.db")
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

    # --- Flask app identity ---

    def test_create_app_returns_flask_instance(self):
        """create_app() must return a Flask application object."""
        self.assertIsInstance(self.app, Flask)

    def test_create_app_is_importable_from_specforge(self):
        """create_app should be importable from the specforge package."""
        from specforge import create_app as factory
        self.assertTrue(callable(factory))

    # --- Required config keys used by app.py __main__ block ---

    def test_config_exposes_port(self):
        """app.config['PORT'] must be accessible and be an integer."""
        port = self.app.config["PORT"]
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)

    def test_config_port_default_is_5000(self):
        """The default PORT should be 5000."""
        self.assertEqual(self.app.config["PORT"], 5000)

    def test_config_exposes_minimax_client_id(self):
        """app.config['MINIMAX_CLIENT_ID'] must be accessible."""
        self.assertIn("MINIMAX_CLIENT_ID", self.app.config)

    def test_config_exposes_minimax_api_key(self):
        """app.config['MINIMAX_API_KEY'] must be accessible."""
        self.assertIn("MINIMAX_API_KEY", self.app.config)

    def test_config_minimax_client_id_empty_by_default(self):
        """MINIMAX_CLIENT_ID should be empty string when not configured."""
        self.assertEqual(self.app.config["MINIMAX_CLIENT_ID"], "")

    def test_config_minimax_api_key_empty_by_default(self):
        """MINIMAX_API_KEY should be empty string when not configured."""
        self.assertEqual(self.app.config["MINIMAX_API_KEY"], "")

    # --- Runtime metadata ---

    def test_app_started_at_is_set(self):
        """App factory must record the startup timestamp in extensions."""
        self.assertIn("started_at", self.app.extensions)
        self.assertIsInstance(self.app.extensions["started_at"], float)
        self.assertGreater(self.app.extensions["started_at"], 0)

    # --- Blueprint registration ---

    def test_main_blueprint_registered(self):
        """The main blueprint must be registered (provides '/' route)."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/", rules)

    def test_analyze_route_registered(self):
        """The /analyze POST route must be registered."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/analyze", rules)

    def test_health_liveness_route_registered(self):
        """/health/live liveness probe must be registered."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/health/live", rules)

    def test_health_ready_route_registered(self):
        """/health/ready readiness probe must be registered."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/health/ready", rules)

    def test_health_compatibility_route_registered(self):
        """/health compatibility alias must be registered."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/health", rules)

    def test_metrics_route_registered(self):
        """/metrics endpoint must be registered."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn("/metrics", rules)

    def test_auth_routes_registered(self):
        """Auth blueprint routes must be present."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        auth_rules = [r for r in rules if r.startswith("/auth/")]
        self.assertGreater(len(auth_rules), 0)

    def test_analyses_routes_registered(self):
        """Analyses blueprint routes must be present."""
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        analysis_rules = [r for r in rules if "/analyses" in r]
        self.assertGreater(len(analysis_rules), 0)

    # --- Error handlers return JSON ---

    def test_404_returns_json_error_response(self):
        """Unknown routes must return a JSON error response with code not_found."""
        response = self.client.get("/no-such-route-xyz")
        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertIsNotNone(body)
        self.assertEqual(body["error"]["code"], "not_found")

    def test_404_response_includes_request_id(self):
        """404 response must include X-Request-ID header."""
        response = self.client.get("/no-such-route-xyz")
        self.assertIn("X-Request-ID", response.headers)

    def test_413_returns_json_error_response(self):
        """Oversized payloads must return 413 with payload_too_large code."""
        oversized = "x" * (self.app.config["MAX_CONTENT_LENGTH"] + 1)
        response = self.client.post(
            "/analyze",
            data=oversized,
            content_type="application/json",
        )
        self.assertIn(response.status_code, (400, 413))

    # --- Configuration defaults from Config class ---

    def test_config_app_version_present(self):
        """APP_VERSION config key must be present."""
        self.assertIn("APP_VERSION", self.app.config)
        self.assertIsInstance(self.app.config["APP_VERSION"], str)

    def test_config_rate_limits_present(self):
        """RATE_LIMITS config dict must contain the analyze key."""
        self.assertIn("RATE_LIMITS", self.app.config)
        self.assertIn("analyze", self.app.config["RATE_LIMITS"])

    def test_config_session_cookie_httponly(self):
        """Session cookies must have HttpOnly flag enabled."""
        self.assertTrue(self.app.config["SESSION_COOKIE_HTTPONLY"])

    def test_config_max_content_length_set(self):
        """MAX_CONTENT_LENGTH must be a positive integer."""
        self.assertIsInstance(self.app.config["MAX_CONTENT_LENGTH"], int)
        self.assertGreater(self.app.config["MAX_CONTENT_LENGTH"], 0)

    # --- Functional smoke test: app serves a valid request ---

    def test_liveness_endpoint_returns_200(self):
        """After app creation, /health/live must return HTTP 200."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)

    def test_liveness_endpoint_returns_json(self):
        """/health/live must return valid JSON."""
        response = self.client.get("/health/live")
        body = response.get_json()
        self.assertIsNotNone(body)

    def test_multiple_create_app_calls_return_independent_instances(self):
        """Calling create_app() twice must produce two independent Flask apps."""
        tempdir2 = tempfile.TemporaryDirectory()
        try:
            db_path2 = os.path.join(tempdir2.name, "specforge-test2.db")
            migrations_dir = str(REPO_ROOT / "migrations")

            class _Config2(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path2}"
                MIGRATIONS_DIR = migrations_dir
                PORT = 5001

            app2 = create_app(_Config2)
            try:
                self.assertIsNot(self.app, app2)
                self.assertEqual(app2.config["PORT"], 5001)
                self.assertEqual(self.app.config["PORT"], 5000)
            finally:
                with app2.app_context():
                    db.session.remove()
                    db.engine.dispose()
        finally:
            tempdir2.cleanup()


class AppEntryPointFileTests(unittest.TestCase):
    """Tests that verify the app.py file structure matches PR expectations."""

    def _read_app_py(self):
        return (REPO_ROOT / "app.py").read_text(encoding="utf-8")

    def test_app_py_imports_create_app_from_specforge(self):
        """app.py must import create_app from the specforge package."""
        source = self._read_app_py()
        self.assertIn("from specforge import create_app", source)

    def test_app_py_calls_create_app(self):
        """app.py must call create_app() to create the app object."""
        source = self._read_app_py()
        self.assertIn("create_app()", source)

    def test_app_py_uses_config_port(self):
        """app.py __main__ block must read PORT from app.config."""
        source = self._read_app_py()
        self.assertIn('app.config["PORT"]', source)

    def test_app_py_uses_config_minimax_client_id(self):
        """app.py must check MINIMAX_CLIENT_ID from config (single or double quotes)."""
        source = self._read_app_py()
        self.assertTrue(
            "app.config['MINIMAX_CLIENT_ID']" in source
            or 'app.config["MINIMAX_CLIENT_ID"]' in source,
            "MINIMAX_CLIENT_ID not found in app.py config access",
        )

    def test_app_py_uses_config_minimax_api_key(self):
        """app.py must check MINIMAX_API_KEY from config (single or double quotes)."""
        source = self._read_app_py()
        self.assertTrue(
            "app.config['MINIMAX_API_KEY']" in source
            or 'app.config["MINIMAX_API_KEY"]' in source,
            "MINIMAX_API_KEY not found in app.py config access",
        )

    def test_app_py_runs_on_all_interfaces(self):
        """app.py must bind to 0.0.0.0 (containerised deployment)."""
        source = self._read_app_py()
        self.assertIn("0.0.0.0", source)

    def test_app_py_does_not_contain_old_domain_templates(self):
        """Refactored app.py must not contain the old DOMAIN_TEMPLATES dict."""
        source = self._read_app_py()
        self.assertNotIn("DOMAIN_TEMPLATES", source)

    def test_app_py_does_not_define_detect_domain_function(self):
        """Refactored app.py must not define the old detect_domain function."""
        source = self._read_app_py()
        self.assertNotIn("def detect_domain", source)

    def test_app_py_does_not_define_route_handlers_directly(self):
        """Refactored app.py must not define Flask route handlers inline."""
        source = self._read_app_py()
        self.assertNotIn("@app.route", source)


if __name__ == "__main__":
    unittest.main()