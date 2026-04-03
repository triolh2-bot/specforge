import os
import tempfile
import unittest

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


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-test.db")
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

    def test_analyze_persists_and_can_be_fetched(self):
        response = self.client.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("analysis_id", body)
        analysis_id = body["analysis_id"]

        saved = self.client.get(f"/api/analyses/{analysis_id}")
        saved_body = saved.get_json()

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved_body["analysis_id"], analysis_id)
        self.assertEqual(saved_body["domain"], "e-commerce")
        self.assertEqual(saved_body["prd"]["title"], "Project Specification Document")

    def test_analysis_history_lists_recent_items(self):
        for domain in ["bakery shop with ordering and payments", "crm for lead tracking and sales dashboard"]:
            self.client.post(
                "/analyze",
                json={
                    "requirements": f"I need a {domain} with admin features and reporting.",
                    "ai_enhance": False,
                    "ai_provider": "minimax",
                },
            )

        response = self.client.get("/api/analyses?limit=10&offset=0")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(body["pagination"]["total"], 2)
        self.assertGreaterEqual(len(body["items"]), 2)

    def test_invalid_history_query_is_rejected(self):
        response = self.client.get("/api/analyses?limit=-1")
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "invalid_query_parameter")


if __name__ == "__main__":
    unittest.main()
