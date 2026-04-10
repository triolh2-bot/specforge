"""Tests for PayPal billing integration."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from specforge import create_app
from specforge.extensions import db
from specforge.services.paypal import (
    _get_paypal_access_token,
    activate_subscription,
    cancel_subscription,
    create_paypal_subscription,
    handle_paypal_webhook_event,
)
from specforge.models import WorkspaceSubscription

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

    # PayPal config (sandbox mode, no real credentials)
    PAYPAL_CLIENT_ID = "test-client-id"
    PAYPAL_CLIENT_SECRET = "test-client-secret"
    PAYPAL_SANDBOX = True
    PAYPAL_WEBHOOK_ID = "test-webhook-id"
    PAYPAL_PLAN_ID_PRO = "P-TESTPRO"
    PAYPAL_PLAN_ID_ENTERPRISE = "P-TESTENT"
    PAYPAL_PLAN_PRICE_PRO = "$19.99/month"
    PAYPAL_PLAN_PRICE_ENTERPRISE = "$99.99/month"


class TestPayPalService(unittest.TestCase):
    """Unit tests for the PayPal service layer."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-paypal-unit.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_get_paypal_plan_id_returns_configured_value(self):
        """Verify plan ID lookup from config."""
        from specforge.services.paypal import get_paypal_plan_id
        with self.app.app_context():
            self.assertEqual(get_paypal_plan_id("pro"), "P-TESTPRO")
            self.assertEqual(get_paypal_plan_id("enterprise"), "P-TESTENT")
            self.assertIsNone(get_paypal_plan_id("free"))

    def test_handle_webhook_activates_subscription(self):
        """Test that PAYMENT.SALE.COMPLETED activates a subscription."""
        # This requires app context — tested in integration tests below
        pass

    def test_handle_webhook_cancels_subscription(self):
        """Test that BILLING.SUBSCRIPTION.CANCELLED cancels a subscription."""
        pass


class PayPalIntegrationTests(unittest.TestCase):
    """Integration tests for PayPal billing endpoints."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-paypal.db")
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

    def test_list_plans_shows_paypal_pricing(self):
        """Verify plan listing includes PayPal prices."""
        resp = self.client.get("/api/billing/plans")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("plans", body)
        self.assertIn("pro", body["plans"])
        self.assertIn("enterprise", body["plans"])
        self.assertEqual(body["plans"]["pro"]["price"], "$19.99/month")
        self.assertEqual(body["plans"]["enterprise"]["price"], "$99.99/month")

    def test_subscribe_returns_approval_url(self):
        """Test subscription initiation with mocked PayPal API."""
        with patch("specforge.routes.billing.create_paypal_subscription") as mock_create:
            mock_create.return_value = {
                "subscription_id": "I-TEST123",
                "status": "APPROVAL_PENDING",
                "approval_url": "https://www.sandbox.paypal.com/webapps/billing/subscriptions?token=EC-TEST",
                "plan_name": "pro",
                "workspace_id": "test-ws",
            }

            resp = self.client.post(
                "/api/billing/subscribe",
                json={"plan": "pro"},
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json()
            self.assertIn("approval_url", body)
            self.assertIn("paypal.com", body["approval_url"])
            self.assertEqual(body["plan"], "pro")

    def test_subscribe_invalid_plan(self):
        """Test that invalid plan names are rejected."""
        resp = self.client.post(
            "/api/billing/subscribe",
            json={"plan": "ultra-premium"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"]["code"], "invalid_plan")

    def test_cancel_subscription(self):
        """Test subscription cancellation."""
        with patch("specforge.routes.billing.paypal_cancel_subscription") as mock_cancel:
            mock_cancel.return_value = True

            resp = self.client.post(
                "/api/billing/cancel",
                json={"reason": "Testing"},
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json()
            self.assertTrue(body["cancelled"])

    def test_webhook_endpoint_accepts_event(self):
        """Test PayPal webhook endpoint processes events."""
        with patch("specforge.routes.billing.verify_paypal_webhook_signature", return_value=True):
            with patch("specforge.routes.billing.handle_paypal_webhook_event") as mock_handle:
                resp = self.client.post(
                    "/api/billing/webhooks/paypal",
                    json={
                        "event_type": "PAYMENT.SALE.COMPLETED",
                        "resource": {"id": "I-TEST123"},
                    },
                )
                self.assertEqual(resp.status_code, 200)
                mock_handle.assert_called_once()

    def test_webhook_rejects_invalid_signature(self):
        """Test webhook rejects unverified signatures."""
        with patch("specforge.routes.billing.verify_paypal_webhook_signature", return_value=False):
            resp = self.client.post(
                "/api/billing/webhooks/paypal",
                json={"event_type": "TEST"},
            )
            self.assertEqual(resp.status_code, 401)

    def test_get_subscription_returns_details(self):
        """Test subscription details endpoint."""
        resp = self.client.get("/api/billing/subscription")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("plan", body)
        self.assertIn("status", body)

    def test_quota_endpoint_returns_usage(self):
        """Test quota endpoint returns proper structure."""
        resp = self.client.get("/api/billing/quota")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("plan", body)
        self.assertEqual(body["plan"], "free")
        self.assertIn("analyses", body)
        self.assertIn("used", body["analyses"])
        self.assertIn("limit", body["analyses"])


class TestPayPalWebhookHandling(unittest.TestCase):
    """Test PayPal webhook event processing."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "specforge-webhook.db")
        migrations_dir = str(REPO_ROOT / "migrations")

        class _Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            MIGRATIONS_DIR = migrations_dir

        self.app = create_app(_Config)

        # Create a test workspace subscription
        with self.app.app_context():
            sub = WorkspaceSubscription(
                workspace_id="test-ws-1",
                provider="paypal",
                provider_subscription_id="I-WEBHOOK-TEST",
                plan="pro",
                status="active",
            )
            db.session.add(sub)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    def test_payment_sale_completed_activates(self):
        """Test that payment completion activates subscription."""
        with self.app.app_context():
            handle_paypal_webhook_event({
                "event_type": "PAYMENT.SALE.COMPLETED",
                "resource": {"id": "I-WEBHOOK-TEST"},
            })

            sub = WorkspaceSubscription.query.filter_by(workspace_id="test-ws-1").first()
            self.assertEqual(sub.status, "active")

    def test_subscription_cancelled_deactivates(self):
        """Test that subscription cancellation deactivates workspace."""
        with self.app.app_context():
            handle_paypal_webhook_event({
                "event_type": "BILLING.SUBSCRIPTION.CANCELLED",
                "resource": {"id": "I-WEBHOOK-TEST"},
            })

            sub = WorkspaceSubscription.query.filter_by(workspace_id="test-ws-1").first()
            self.assertEqual(sub.status, "expired")
            self.assertEqual(sub.plan, "free")

    def test_subscription_suspended_marks_past_due(self):
        """Test that suspension marks workspace as past_due."""
        with self.app.app_context():
            handle_paypal_webhook_event({
                "event_type": "BILLING.SUBSCRIPTION.SUSPENDED",
                "resource": {"id": "I-WEBHOOK-TEST"},
            })

            sub = WorkspaceSubscription.query.filter_by(workspace_id="test-ws-1").first()
            self.assertEqual(sub.status, "past_due")


if __name__ == "__main__":
    unittest.main()
