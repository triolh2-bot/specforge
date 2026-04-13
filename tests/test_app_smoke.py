"""Whole-app smoke test covering the primary user flow."""

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
    OPENROUTER_SITE_URL = ""

    PAYPAL_CLIENT_ID = ""
    PAYPAL_CLIENT_SECRET = ""
    PAYPAL_SANDBOX = True
    PAYPAL_WEBHOOK_ID = ""
    PAYPAL_PLAN_ID_PRO = ""
    PAYPAL_PLAN_ID_ENTERPRISE = ""


class AppSmokeTests(unittest.TestCase):
    def setUp(self):
        tmp_dir = REPO_ROOT / "tests" / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        self.db_path = tmp_dir / "specforge-app-smoke.db"
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

    def post_json(self, path, payload):
        return self.client.post(path, json=payload, headers=self.same_origin_headers)

    def post_empty(self, path):
        return self.client.post(path, headers=self.same_origin_headers)

    def test_complete_application_smoke_flow(self):
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertIn("SpecForge", index.get_data(as_text=True))

        for path in ("/health", "/health/live", "/health/ready"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)

        quota_resp = self.client.get("/api/billing/quota")
        self.assertEqual(quota_resp.status_code, 200)
        self.assertEqual(quota_resp.get_json()["plan"], "free")

        plans_resp = self.client.get("/api/billing/plans")
        self.assertEqual(plans_resp.status_code, 200)
        plans_body = plans_resp.get_json()
        self.assertIn("pro", plans_body["plans"])
        self.assertIn("enterprise", plans_body["plans"])

        with patch("specforge.routes.main.generate_brief", return_value={
            "success": True,
            "brief": "A collaborative meal-planning app for busy households.",
            "provider": "mock-provider",
        }):
            brief_resp = self.post_json(
                "/api/generate-brief",
                {
                    "project_name": "PlanPlate",
                    "project_type": "Web Application",
                    "core_idea": "Help families plan meals, share grocery lists, and track weekly dinner plans.",
                    "target_audience": "Busy households",
                    "key_features": "Meal calendar, grocery list, shared household access",
                    "ai_provider": "openrouter",
                },
            )
        self.assertEqual(brief_resp.status_code, 200)
        self.assertEqual(brief_resp.get_json()["brief"], "A collaborative meal-planning app for busy households.")

        analyze_resp = self.post_json(
            "/analyze",
            {
                "requirements": (
                    "Build a collaborative meal-planning web app with household accounts, "
                    "shared grocery lists, weekly meal calendars, notifications, and an admin dashboard."
                ),
                "ai_enhance": False,
                "ai_provider": "openrouter",
                "target_users": "Families, household admins",
                "business_goal": "Reduce meal planning friction and improve grocery coordination.",
                "success_metrics": "Weekly active households, list completion rate",
            },
        )
        self.assertEqual(analyze_resp.status_code, 200)
        analysis_body = analyze_resp.get_json()
        analysis_id = analysis_body["analysis_id"]
        self.assertTrue(analysis_id)
        self.assertIn("prd", analysis_body)
        self.assertIn("domain", analysis_body)
        self.assertGreaterEqual(analysis_body["rms"], 0)

        history_resp = self.client.get("/api/analyses?limit=10&offset=0")
        self.assertEqual(history_resp.status_code, 200)
        history_body = history_resp.get_json()
        history_ids = [item["analysis_id"] for item in history_body["items"]]
        self.assertIn(analysis_id, history_ids)

        detail_resp = self.client.get(f"/api/analyses/{analysis_id}?include_versions=true")
        self.assertEqual(detail_resp.status_code, 200)
        detail_body = detail_resp.get_json()
        self.assertEqual(detail_body["analysis_id"], analysis_id)
        self.assertIn("versions", detail_body)

        approve_resp = self.post_json(f"/api/analyses/{analysis_id}/approve", {})
        self.assertEqual(approve_resp.status_code, 200)
        approve_body = approve_resp.get_json()
        self.assertEqual(approve_body["analysis_id"], analysis_id)
        self.assertEqual(approve_body["approval_state"], "approved")
        self.assertIsNotNone(approve_body["approved_version"])

        export_resp = self.post_json(
            "/api/exports",
            {
                "analysis_id": analysis_id,
                "format": "markdown",
            },
        )
        self.assertEqual(export_resp.status_code, 201)
        export_body = export_resp.get_json()
        export_id = export_body["export_id"]
        self.assertTrue(export_body["share_url"].startswith("/api/exports/share/"))

        exports_resp = self.client.get("/api/exports")
        self.assertEqual(exports_resp.status_code, 200)
        exports_body = exports_resp.get_json()
        export_ids = [item["export_id"] for item in exports_body["items"]]
        self.assertIn(export_id, export_ids)

        download_resp = self.client.get(f"/api/exports/{export_id}/download")
        self.assertEqual(download_resp.status_code, 200)
        self.assertIn("attachment;", download_resp.headers.get("Content-Disposition", ""))
        self.assertIn("#", download_resp.get_data(as_text=True))

        shared_resp = self.client.get(export_body["share_url"])
        self.assertEqual(shared_resp.status_code, 200)
        self.assertIn("#", shared_resp.get_data(as_text=True))

        data_export_resp = self.post_empty("/api/legal/data-export")
        self.assertEqual(data_export_resp.status_code, 200)
        data_export_body = data_export_resp.get_json()["export"]
        self.assertIn(analysis_id, [item["id"] for item in data_export_body["analyses"]])
        self.assertIn(export_id, [item["id"] for item in data_export_body["exports"]])

        consent_resp = self.client.get("/api/legal/consent")
        self.assertEqual(consent_resp.status_code, 200)
        consent_body = consent_resp.get_json()
        self.assertIn("analytics_consent", consent_body)
        self.assertIn("policies_accepted", consent_body)


if __name__ == "__main__":
    unittest.main()
