import io
import json
import logging
import os
import tempfile
import unittest

from specforge import create_app
from specforge.extensions import db


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
    LOG_LEVEL = "INFO"


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-observability.db")
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

    def test_metrics_endpoint_reports_counters(self):
        self.client.get("/health")
        self.client.get("/metrics")
        response = self.client.get("/metrics")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("counters", body)
        self.assertGreaterEqual(body["counters"]["http_requests_total"], 2)

    def test_request_logging_is_structured_json(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root_logger = logging.getLogger()
        previous_handlers = list(root_logger.handlers)
        root_logger.handlers = [handler]
        try:
            self.app = create_app(type("Config", (TestConfig,), {
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{os.path.join(self.tempdir.name, 'structured.db')}",
                "MIGRATIONS_DIR": os.path.join("/home/kali/.openclaw/workspace/specforge-mvp", "migrations"),
            }))
            client = self.app.test_client()
            client.get("/health")
            log_output = stream.getvalue().strip().splitlines()[-1]
            payload = json.loads(log_output)

            self.assertEqual(payload["event"], "http_request")
            self.assertEqual(payload["path"], "/health")
            self.assertEqual(payload["status_code"], 200)
            self.assertIn("duration_ms", payload)
        finally:
            root_logger.handlers = previous_handlers


if __name__ == "__main__":
    unittest.main()
