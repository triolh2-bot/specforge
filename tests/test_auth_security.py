import os
import tempfile
import unittest
from pathlib import Path

from flask import session

from specforge import create_app
from specforge.extensions import db
from specforge.repositories.auth_repository import get_auth_session_credential
from specforge.services.auth_session import (
    ensure_workspace_context,
    get_auth_status,
    get_or_create_auth_session_id,
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


class AuthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-auth.db")
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

    def test_workspace_context_creates_server_side_credential(self):
        with self.app.test_request_context("/"):
            context = ensure_workspace_context()
            auth_session_id = get_or_create_auth_session_id()
            credential = get_auth_session_credential(auth_session_id)

            self.assertIsNotNone(credential)
            self.assertEqual(credential.workspace_id, context["workspace_id"])
            self.assertEqual(credential.provider, "session")
            self.assertIsNone(credential.encrypted_access_token)
            self.assertIsNone(credential.encrypted_refresh_token)

    def test_logout_clears_browser_session(self):
        with self.app.test_request_context("/"):
            session["auth_session_id"] = "session-123"
            ensure_workspace_context()

        with self.client.session_transaction() as client_session:
            client_session["auth_session_id"] = "session-123"
            client_session["workspace_id"] = "workspace-123"
            client_session["workspace_role"] = "owner"

        response = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as client_session:
            self.assertNotIn("auth_session_id", client_session)
            self.assertNotIn("workspace_id", client_session)
            self.assertNotIn("workspace_role", client_session)

    def test_auth_status_uses_server_side_credentials(self):
        with self.app.test_request_context("/"):
            session["auth_session_id"] = "session-abc"
            ensure_workspace_context()
            auth_state = get_auth_status()

        with self.client.session_transaction() as client_session:
            client_session["auth_session_id"] = "session-abc"

        response = self.client.get("/auth/status")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["token_expires_in"], 0)
        self.assertEqual(body["workspace_id"], auth_state["workspace_id"])
        self.assertEqual(body["role"], "owner")


if __name__ == "__main__":
    unittest.main()
