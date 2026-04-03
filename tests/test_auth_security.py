import os
import tempfile
import unittest

from flask import session

from specforge import create_app
from specforge.extensions import db
from specforge.repositories.auth_repository import get_auth_session_credential
from specforge.services.auth_session import get_or_create_auth_session_id, get_valid_minimax_access_token, store_minimax_tokens


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


class AuthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-auth.db")
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

    def test_tokens_are_stored_encrypted_and_can_be_loaded(self):
        with self.app.test_request_context("/"):
            auth_session_id = get_or_create_auth_session_id()
            store_minimax_tokens("access-token-plain", refresh_token="refresh-token-plain", expires_in=3600)
            credential = get_auth_session_credential(auth_session_id)

            self.assertNotEqual(credential.encrypted_access_token, "access-token-plain")
            self.assertNotEqual(credential.encrypted_refresh_token, "refresh-token-plain")
            self.assertEqual(get_valid_minimax_access_token(), "access-token-plain")

    def test_logout_clears_server_side_credentials(self):
        with self.client.session_transaction() as client_session:
            client_session["auth_session_id"] = "session-123"
            client_session["minimax_authenticated"] = True

        with self.app.test_request_context("/"):
            session["auth_session_id"] = "session-123"
            store_minimax_tokens("access-token-plain", refresh_token="refresh-token-plain", expires_in=3600)

        response = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            self.assertIsNone(get_auth_session_credential("session-123"))

    def test_auth_status_uses_server_side_credentials(self):
        with self.client.session_transaction() as client_session:
            client_session["auth_session_id"] = "session-abc"

        with self.app.test_request_context("/"):
            session["auth_session_id"] = "session-abc"
            store_minimax_tokens("access-token-plain", refresh_token="refresh-token-plain", expires_in=3600)

        response = self.client.get("/auth/status")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["authenticated"])
        self.assertGreater(body["token_expires_in"], 0)


if __name__ == "__main__":
    unittest.main()
