"""Tests for server-side export and sharing."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from specforge import create_app
from specforge.extensions import db
from specforge.services.exports import (
    generate_export,
    generate_html_export,
    generate_json_export,
    generate_markdown_export,
    SUPPORTED_FORMATS,
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


class TestExportGeneration(unittest.TestCase):
    """Unit tests for export format generators."""

    def setUp(self):
        self.analysis = {
            "domain": "e-commerce",
            "rms": 72,
            "implied_users": ["Admin", "Customer"],
            "missing_features": ["Shipping calculation", "Refund workflow"],
            "clarification_questions": [
                "What payment providers?",
                "Shipping providers?",
                "Inventory management?",
            ],
            "conflicts": ["Fast delivery vs complex features"],
            "prd": {
                "title": "E-Commerce PRD",
                "version": "1.0",
                "overview": {
                    "summary": "An online store for custom products.",
                    "project_type": "e-commerce",
                    "target_users": ["Admin", "Customer"],
                },
                "scope": {
                    "in_scope": ["Product catalog", "Shopping cart", "Checkout"],
                    "out_of_scope": ["Mobile apps", "AI features"],
                },
                "functional_requirements": [
                    "User registration",
                    "Product browsing",
                    "Cart management",
                    "Payment processing",
                ],
                "non_functional": {
                    "performance": "Page load under 3 seconds",
                    "security": "HTTPS and encryption",
                },
                "technical_constraints": {
                    "timeline": "8-12 weeks",
                    "tech_stack": "React + Node.js + PostgreSQL",
                },
                "risks": ["Scope creep", "Payment integration issues"],
            },
        }

    def test_markdown_export_contains_sections(self):
        content, filename = generate_markdown_export(self.analysis)
        self.assertIn("# E-Commerce PRD", content)
        self.assertIn("## Overview", content)
        self.assertIn("## Functional Requirements", content)
        self.assertIn("## Risks", content)
        self.assertIn("## Clarification Questions", content)
        self.assertIn("An online store for custom products", content)
        self.assertTrue(filename.endswith(".md"))

    def test_html_export_is_valid_html(self):
        content, filename = generate_html_export(self.analysis)
        self.assertTrue(content.startswith("<!DOCTYPE html>"))
        self.assertIn("</html>", content)
        self.assertIn("E-Commerce PRD", content)
        self.assertIn("E-Commerce", content)
        self.assertTrue(filename.endswith(".html"))

    def test_json_export_is_valid_json(self):
        content, filename = generate_json_export(self.analysis)
        data = json.loads(content)
        self.assertIn("metadata", data)
        self.assertIn("analysis", data)
        self.assertIn("prd", data)
        self.assertEqual(data["analysis"]["domain"], "e-commerce")
        self.assertEqual(data["analysis"]["rms"], 72)
        self.assertTrue(filename.endswith(".json"))

    def test_unsupported_format_raises(self):
        with self.assertRaises(ValueError):
            generate_export(self.analysis, "pdf")

    def test_generate_export_dispatches_correctly(self):
        for fmt in SUPPORTED_FORMATS:
            content, filename = generate_export(self.analysis, fmt)
            self.assertTrue(len(content) > 0)
            self.assertTrue(len(filename) > 0)


class ExportIntegrationTests(unittest.TestCase):
    """Integration tests for export endpoints."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-export.db")
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

    def _create_analysis(self):
        return self.client.post(
            "/analyze",
            json={
                "requirements": "Build an e-commerce store with cart and checkout.",
                "ai_enhance": False,
                "ai_provider": "openrouter",
            },
        )

    def test_create_export_returns_201(self):
        resp = self._create_analysis()
        self.assertEqual(resp.status_code, 200)
        analysis_id = resp.get_json()["analysis_id"]

        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": analysis_id, "format": "markdown"},
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertIn("export_id", body)
        self.assertIn("share_url", body)
        self.assertEqual(body["format"], "markdown")

    def test_create_export_all_formats(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        for fmt in SUPPORTED_FORMATS:
            resp = self.client.post(
                "/api/exports",
                json={"analysis_id": analysis_id, "format": fmt},
            )
            self.assertEqual(resp.status_code, 201, f"Failed for format: {fmt}")

    def test_create_export_missing_analysis_id(self):
        resp = self.client.post("/api/exports", json={})
        self.assertEqual(resp.status_code, 400)

    def test_create_export_unsupported_format(self):
        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": "fake-id", "format": "pdf"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"]["code"], "unsupported_format")

    def test_create_export_analysis_not_found(self):
        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": "nonexistent-id", "format": "markdown"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_download_export(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        # Create export
        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": analysis_id, "format": "markdown"},
        )
        export_id = resp.get_json()["export_id"]

        # Download
        resp = self.client.get(f"/api/exports/{export_id}/download")
        self.assertEqual(resp.status_code, 200)
        content = resp.get_data(as_text=True)
        self.assertIn("Project Specification Document", content)

    def test_download_export_not_found(self):
        resp = self.client.get("/api/exports/nonexistent/download")
        self.assertEqual(resp.status_code, 404)

    def test_share_export_via_token(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        resp = self.client.post(
            "/api/exports",
            json={"analysis_id": analysis_id, "format": "html"},
        )
        share_url = resp.get_json()["share_url"]

        # Access via share token (no auth required)
        token = share_url.split("/")[-1]
        resp = self.client.get(f"/api/exports/share/{token}")
        self.assertEqual(resp.status_code, 200)
        content = resp.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", content)

    def test_share_token_not_found(self):
        resp = self.client.get("/api/exports/share/nonexistent-token")
        self.assertEqual(resp.status_code, 404)

    def test_list_exports(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        self.client.post("/api/exports", json={"analysis_id": analysis_id, "format": "markdown"})
        self.client.post("/api/exports", json={"analysis_id": analysis_id, "format": "json"})

        resp = self.client.get("/api/exports")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["pagination"]["total"], 2)
        self.assertEqual(len(body["items"]), 2)

    def test_create_share_link(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        resp = self.client.post(
            f"/api/analyses/{analysis_id}/share",
            json={"expires_days": 14, "access_level": "view"},
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertIn("share_url", body)
        self.assertEqual(body["access_level"], "view")

    def test_list_share_links(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        self.client.post(f"/api/analyses/{analysis_id}/share", json={})
        self.client.post(f"/api/analyses/{analysis_id}/share", json={})

        resp = self.client.get(f"/api/analyses/{analysis_id}/shares")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["count"], 2)

    def test_invalid_share_access_level(self):
        resp = self._create_analysis()
        analysis_id = resp.get_json()["analysis_id"]

        resp = self.client.post(
            f"/api/analyses/{analysis_id}/share",
            json={"access_level": "delete"},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
