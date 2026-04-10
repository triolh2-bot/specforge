"""Tests for billing, quotas, and plan enforcement."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from specforge import create_app
from specforge.extensions import db
from specforge.services.billing import (
    check_provider_allowed,
    check_quota,
    consume_quota,
    get_plan_limits,
    get_quota_status,
    get_workspace_plan,
    PLANS,
    QuotaExceededError,
)
from specforge.repositories.workspace_repository import upsert_workspace_subscription

REPO_ROOT = Path(__file__).resolve().parent.parent


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


class TestPlanLimits(unittest.TestCase):
    def test_all_plans_defined(self):
        self.assertIn("free", PLANS)
        self.assertIn("pro", PLANS)
        self.assertIn("enterprise", PLANS)

    def test_free_plan_has_limits(self):
        limits = get_plan_limits("free")
        self.assertLess(limits.analyses_per_month, 100)
        self.assertLess(limits.ai_enhancements_per_month, 50)

    def test_enterprise_plan_has_high_limits(self):
        limits = get_plan_limits("enterprise")
        self.assertGreater(limits.analyses_per_month, 10000)
        self.assertTrue(limits.priority_queue)

    def test_pro_has_more_than_free(self):
        free = get_plan_limits("free")
        pro = get_plan_limits("pro")
        self.assertGreater(pro.analyses_per_month, free.analyses_per_month)
        self.assertGreater(pro.ai_enhancements_per_month, free.ai_enhancements_per_month)

    def test_unknown_plan_defaults_to_free(self):
        limits = get_plan_limits("nonexistent_plan_xyz")
        self.assertEqual(limits, get_plan_limits("free"))


class TestQuotaEnforcement(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-billing.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)
        self.workspace_id = "test-workspace"

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_check_quota_allows_under_limit(self):
        with self.app.app_context():
            # Free plan allows 10 analyses, we haven't used any
            check_quota(self.workspace_id, "analysis")  # Should not raise

    def test_consume_quota_tracks_usage(self):
        with self.app.app_context():
            consume_quota(self.workspace_id, "analysis")
            status = get_quota_status(self.workspace_id)
            self.assertEqual(status["analyses"]["used"], 1)

    def test_consume_quota_raises_when_exceeded(self):
        with self.app.app_context():
            # Free plan allows 10 analyses
            for _ in range(10):
                consume_quota(self.workspace_id, "analysis")

            with self.assertRaises(QuotaExceededError) as ctx:
                consume_quota(self.workspace_id, "analysis")

            self.assertEqual(ctx.exception.metric, "analysis")
            self.assertEqual(ctx.exception.limit, 10)
            self.assertEqual(ctx.exception.current, 10)
            self.assertEqual(ctx.exception.plan, "free")

    def test_pro_plan_has_higher_limits(self):
        with self.app.app_context():
            upsert_workspace_subscription(self.workspace_id, "pro")

            # Use 10 analyses (free limit)
            for _ in range(10):
                consume_quota(self.workspace_id, "analysis")

            # Should still work on pro plan (limit 100)
            consume_quota(self.workspace_id, "analysis")

            status = get_quota_status(self.workspace_id)
            self.assertEqual(status["plan"], "pro")
            self.assertEqual(status["analyses"]["used"], 11)
            self.assertEqual(status["analyses"]["limit"], 100)

    def test_check_provider_allowed_for_free_plan(self):
        with self.app.app_context():
            self.assertTrue(check_provider_allowed(self.workspace_id, "minimax"))

    def test_workspace_plan_defaults_free(self):
        with self.app.app_context():
            plan = get_workspace_plan(self.workspace_id)
            self.assertEqual(plan, "free")


class BillingIntegrationTests(unittest.TestCase):
    """Integration tests for billing endpoints."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-billing.db")
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

    def _analyze(self, requirements="Build an e-commerce store with cart and checkout."):
        return self.client.post(
            "/analyze",
            json={
                "requirements": requirements,
                "ai_enhance": False,
                "ai_provider": "minimax",
            },
        )

    def test_quota_endpoint_returns_200(self):
        resp = self.client.get("/api/billing/quota")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("plan", body)
        self.assertEqual(body["plan"], "free")
        self.assertIn("analyses", body)
        self.assertIn("limit", body["analyses"])

    def test_plans_endpoint_returns_all_plans(self):
        resp = self.client.get("/api/billing/plans")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("plans", body)
        self.assertIn("free", body["plans"])
        self.assertIn("pro", body["plans"])
        self.assertIn("enterprise", body["plans"])

    def test_quota_check_dry_run(self):
        resp = self.client.post(
            "/api/billing/quota/check",
            json={"metric": "analysis"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["allowed"])

    def test_provider_check_endpoint(self):
        resp = self.client.post(
            "/api/billing/provider/check",
            json={"provider": "minimax"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["allowed"])

    def test_analyze_respects_quota(self):
        with self.app.app_context():
            from specforge.repositories.workspace_repository import upsert_workspace_subscription
            upsert_workspace_subscription("ws-1", "free")

        # Use up all quota
        for _ in range(10):
            self._analyze()

        # Next analysis should fail with quota exceeded
        resp = self._analyze()
        body = resp.get_json()
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(body["error"]["code"], "quota_exceeded")


if __name__ == "__main__":
    unittest.main()
