import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from specforge import create_app
from specforge.extensions import db
from specforge.services.job_queue import process_next_job

REPO_ROOT = Path(__file__).resolve().parent.parent


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


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-jobs.db")
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

    def test_ai_analysis_request_is_enqueued(self):
        response = self.client.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": True,
                "ai_provider": "minimax",
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(body["status"], "queued")
        self.assertIn("job_id", body)

        job_response = self.client.get(f"/api/jobs/{body['job_id']}")
        job_body = job_response.get_json()
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_body["status"], "queued")

    def test_worker_processes_queued_job(self):
        response = self.client.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": True,
                "ai_provider": "minimax",
            },
        )
        job_id = response.get_json()["job_id"]

        mock_result = {
            "success": True,
            "domain": "e-commerce",
            "implied_users": ["Admin", "Customer"],
            "missing_features": ["Shipping calculation"],
            "clarification_questions": ["What shipping providers will you use?"],
            "conflicts": [],
            "rms": 75,
            "prd": {
                "title": "Project Specification Document",
                "version": "1.0",
                "overview": {"summary": "Mock summary", "project_type": "e-commerce", "target_users": ["Admin", "Customer"]},
                "scope": {"in_scope": ["Core e-commerce functionality"], "out_of_scope": ["Advanced AI/ML features"]},
                "functional_requirements": ["Shopping cart functionality"],
                "non_functional": {
                    "performance": "Page load under 3 seconds",
                    "security": "HTTPS, secure authentication, data encryption",
                    "scalability": "Support 1000+ concurrent users initially",
                    "reliability": "99.9% uptime target",
                },
                "technical_constraints": {
                    "timeline": "8-12 weeks",
                    "budget": "To be determined",
                    "team_size": "1-3 developers recommended",
                    "tech_stack": None,
                },
                "risks": ["Scope creep from unclear requirements"],
                "next_steps": ["Answer clarification questions"],
            },
            "ai_enhanced": {"status": "success", "provider": "minimax", "data": {"estimated_timeline": "8-12 weeks"}},
            "ai_providers": {"minimax": {"oauth_enabled": False, "api_key_enabled": False, "models": ["MiniMax-M2.5"]}},
        }

        with self.app.app_context():
            with patch("specforge.services.job_queue.generate_prd", return_value=mock_result):
                processed = process_next_job()

        self.assertEqual(processed["status"], "completed")
        self.assertIsNotNone(processed["analysis_id"])

        job_response = self.client.get(f"/api/jobs/{job_id}")
        job_body = job_response.get_json()
        self.assertEqual(job_body["status"], "completed")
        self.assertEqual(job_body["analysis_id"], processed["analysis_id"])

        analysis_response = self.client.get(f"/api/analyses/{processed['analysis_id']}")
        self.assertEqual(analysis_response.status_code, 200)

    def test_job_processing_failure_marks_job_failed(self):
        response = self.client.post(
            "/analyze",
            json={
                "requirements": "I want an e-commerce site for my bakery with ordering and an admin dashboard.",
                "ai_enhance": True,
                "ai_provider": "minimax",
            },
        )
        job_id = response.get_json()["job_id"]

        with self.app.app_context():
            with patch("specforge.services.job_queue.generate_prd", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    process_next_job()
                with self.assertRaises(RuntimeError):
                    process_next_job()
                with self.assertRaises(RuntimeError):
                    process_next_job()

        job_response = self.client.get(f"/api/jobs/{job_id}")
        job_body = job_response.get_json()
        self.assertEqual(job_body["status"], "failed")
        self.assertEqual(job_body["attempt_count"], 3)
        self.assertIn("boom", job_body["error_message"])


if __name__ == "__main__":
    unittest.main()
