"""PayPal billing integration — subscriptions, webhooks, and plan mapping.

Provides:
- PayPal Checkout / Subscription creation
- Webhook handler for payment events (PAYMENT.SALE.COMPLETED,
  BILLING.SUBSCRIPTION.CANCELLED, etc.)
- Plan mapping between SpecForge tiers and PayPal plan IDs
- Workspace subscription lifecycle management
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from flask import current_app, request

from ..extensions import db
from ..models import WorkspaceSubscription
from ..services.billing import PLANS, PlanLimits

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PayPal API helpers
# ---------------------------------------------------------------------------

_PAYPAL_BASE = "https://api-m.paypal.com"
_PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


def _paypal_base_url() -> str:
    """Return the PayPal API base URL based on sandbox config."""
    if current_app.config.get("PAYPAL_SANDBOX", True):
        return _PAYPAL_SANDBOX_BASE
    return _PAYPAL_BASE


def _paypal_auth_url() -> str:
    return f"{_paypal_base_url()}/v1/oauth2/token"


def _paypal_api_url(path: str) -> str:
    return f"{_paypal_base_url()}{path}"


def _get_paypal_access_token() -> Optional[str]:
    """Obtain a PayPal OAuth2 access token using client credentials."""
    client_id = current_app.config.get("PAYPAL_CLIENT_ID", "")
    client_secret = current_app.config.get("PAYPAL_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.warning("PayPal credentials not configured")
        return None

    try:
        resp = requests.post(
            _paypal_auth_url(),
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:
        logger.error("PayPal token request failed: %s", exc)
        return None


def _paypal_headers(access_token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "PayPal-Request-Id": str(uuid.uuid4()),  # Idempotency key
    }


# ---------------------------------------------------------------------------
# Plan mapping
# ---------------------------------------------------------------------------

# Mapping from SpecForge plan names to PayPal plan IDs (set via config)
# PAYPAL_PLAN_ID_FREE, PAYPAL_PLAN_ID_PRO, PAYPAL_PLAN_ID_ENTERPRISE

def get_paypal_plan_id(plan_name: str) -> Optional[str]:
    """Return the PayPal plan/product ID for a SpecForge plan."""
    config_key = f"PAYPAL_PLAN_ID_{plan_name.upper()}"
    return current_app.config.get(config_key)


def get_plan_price(plan_name: str) -> Optional[str]:
    """Return the human-readable price for a plan."""
    config_key = f"PAYPAL_PLAN_PRICE_{plan_name.upper()}"
    return current_app.config.get(config_key)


def is_paypal_configured() -> bool:
    """Return True when the shared PayPal credentials are configured."""
    client_id = current_app.config.get("PAYPAL_CLIENT_ID", "")
    client_secret = current_app.config.get("PAYPAL_CLIENT_SECRET", "")
    return bool(client_id and client_secret)


def is_paypal_plan_available(plan_name: str) -> bool:
    """Return True when checkout can be started for the given plan."""
    return is_paypal_configured() and bool(get_paypal_plan_id(plan_name))


# ---------------------------------------------------------------------------
# Subscription creation
# ---------------------------------------------------------------------------

def create_paypal_subscription(
    workspace_id: str,
    plan_name: str,
    payer_email: str,
    return_url: str,
    cancel_url: str,
) -> Optional[dict[str, Any]]:
    """Create a PayPal billing subscription for the given workspace.

    Returns a dict with ``approval_url`` that the user must visit to approve.
    """
    paypal_plan_id = get_paypal_plan_id(plan_name)
    if not paypal_plan_id:
        logger.warning("No PayPal plan ID configured for plan '%s'", plan_name)
        return None

    access_token = _get_paypal_access_token()
    if not access_token:
        return None

    # Create the subscription
    payload = {
        "plan_id": paypal_plan_id,
        "application_context": {
            "brand_name": "SpecForge",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "payment_method": {
                "payer_selected": "PAYPAL",
            },
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
        "subscriber": {
            "email_address": payer_email,
        },
    }

    try:
        resp = requests.post(
            _paypal_api_url("/v1/billing/subscriptions"),
            headers=_paypal_headers(access_token),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        # Extract approval URL
        approval_url = None
        for link in result.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link["href"]
                break

        return {
            "subscription_id": result.get("id"),
            "status": result.get("status"),
            "approval_url": approval_url,
            "plan_name": plan_name,
            "workspace_id": workspace_id,
        }

    except Exception as exc:
        logger.error("PayPal subscription creation failed: %s", exc)
        return None


def activate_subscription(workspace_id: str, subscription_id: str, plan_name: str) -> None:
    """Mark a workspace subscription as active after PayPal approval."""
    sub = WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).first()
    if sub is None:
        sub = WorkspaceSubscription(workspace_id=workspace_id)
        db.session.add(sub)

    sub.plan = plan_name
    sub.status = "active"
    sub.provider = "paypal"
    sub.provider_subscription_id = subscription_id
    sub.current_period_start = datetime.now(timezone.utc)
    # Default 30-day billing cycle
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    db.session.commit()
    logger.info("PayPal subscription activated: workspace=%s, plan=%s", workspace_id, plan_name)


def cancel_subscription(workspace_id: str, reason: str = "Cancelled by user") -> bool:
    """Cancel the PayPal subscription for a workspace."""
    sub = WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).first()
    if not sub or sub.provider != "paypal" or not sub.provider_subscription_id:
        return False

    access_token = _get_paypal_access_token()
    if not access_token:
        return False

    try:
        resp = requests.post(
            _paypal_api_url(f"/v1/billing/subscriptions/{sub.provider_subscription_id}/cancel"),
            headers=_paypal_headers(access_token),
            json={"reason": reason},
            timeout=15,
        )
        # PayPal returns 204 on success
        resp.raise_for_status()

        # Only update local state after successful PayPal response
        sub.status = "canceled"
        sub.canceled_at = datetime.now(timezone.utc)
        sub.plan = "free"
        db.session.commit()
        return True

    except Exception as exc:
        logger.error("PayPal subscription cancellation failed: %s", exc)
        db.session.rollback()
        return False


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------

def verify_paypal_webhook_signature() -> bool:
    """Verify the PayPal webhook signature to ensure the request is authentic.

    In sandbox mode, performs basic header validation.
    In production mode, verifies the HMAC signature using PayPal's public certificate.
    """
    transmission_id = request.headers.get("PAYPAL-TRANSMISSION-ID", "")
    transmission_sig = request.headers.get("PAYPAL-TRANSMISSION-SIG", "")
    transmission_time = request.headers.get("PAYPAL-TRANSMISSION-TIME", "")
    cert_url = request.headers.get("PAYPAL-CERT-URL", "")
    auth_algo = request.headers.get("PAYPAL-AUTH-ALGO", "")

    webhook_id = current_app.config.get("PAYPAL_WEBHOOK_ID", "")
    body = request.get_data()

    if not all([transmission_id, transmission_sig, transmission_time, cert_url, auth_algo, webhook_id]):
        logger.warning("PayPal webhook verification: missing required headers")
        return False

    # Sandbox mode: accept with a warning logged (no real signature verification needed)
    if current_app.config.get("PAYPAL_SANDBOX", True):
        logger.info(
            "PayPal webhook received (sandbox): transmission_id=%s, event=%s",
            transmission_id,
            (request.get_json(silent=True) or {}).get("event_type", "unknown"),
        )
        return True

    # Production mode: verify HMAC signature using PayPal's certificate
    try:
        # Validate certificate URL to prevent SSRF
        from urllib.parse import urlparse
        parsed_url = urlparse(cert_url)
        allowed_hosts = {"api-m.paypal.com", "api.sandbox.paypal.com"}
        if parsed_url.scheme != "https" or parsed_url.hostname not in allowed_hosts:
            logger.error("PayPal webhook: invalid certificate URL scheme or host: %s", cert_url)
            return False

        # Download the certificate from PayPal
        cert_resp = requests.get(cert_url, timeout=10)
        cert_resp.raise_for_status()

        # Parse the certificate chain
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization

        # The cert_url returns a JSON response with multiple certificates.
        # We need to find the one whose fingerprint matches the transmission.
        certs_data = cert_resp.json()

        # Build the signature data string exactly as PayPal specifies
        sig_data = (
            f"{transmission_id}\n"
            f"{transmission_time}\n"
            f"{webhook_id}\n"
            f"{hashlib.sha256(body).hexdigest()}"
        )

        # Try each certificate in the response
        for cert_entry in certs_data.get("certificates", []):
            cert_pem = cert_entry.get("certificate", "")
            cert = x509.load_pem_x509_certificate(cert_pem.encode())

            # Verify the signature
            public_key = cert.public_key()
            if auth_algo == "SHA256withRSA":
                from cryptography.hazmat.primitives.asymmetric import padding
                public_key.verify(
                    base64.b64decode(transmission_sig),
                    sig_data.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                # Signature verified successfully
                logger.info(
                    "PayPal webhook signature verified: transmission_id=%s",
                    transmission_id,
                )
                return True

        logger.error("PayPal webhook: no certificate matched the signature")
        return False

    except ImportError:
        logger.error(
            "PayPal webhook: 'cryptography' package required for production signature verification. "
            "Install with: pip install cryptography"
        )
        return False
    except Exception as exc:
        logger.error("PayPal webhook signature verification failed: %s", exc)
        return False


def handle_paypal_webhook_event(event: dict[str, Any]) -> None:
    """Process a PayPal webhook event and update subscription status."""
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})
    subscription_id = resource.get("id") or resource.get("billing_agreement_id", "")
    custom_id = resource.get("custom_id", "")

    logger.info("PayPal webhook event: %s, subscription_id=%s", event_type, subscription_id)

    # Find the workspace by provider_subscription_id
    sub = None
    if subscription_id:
        sub = WorkspaceSubscription.query.filter_by(
            provider_subscription_id=subscription_id
        ).first()
    elif custom_id:
        # custom_id can be set to workspace_id during subscription creation
        sub = WorkspaceSubscription.query.filter_by(workspace_id=custom_id).first()

    if not sub:
        logger.warning("No workspace subscription found for PayPal event %s", event_type)
        return

    if event_type in ("PAYMENT.SALE.COMPLETED", "BILLING.SUBSCRIPTION.ACTIVATED"):
        sub.status = "active"
        sub.current_period_start = datetime.now(timezone.utc)
        sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        logger.info("PayPal subscription activated: workspace=%s", sub.workspace_id)

    elif event_type in ("BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED"):
        sub.status = "expired"
        sub.canceled_at = datetime.now(timezone.utc)
        sub.plan = "free"
        logger.info("PayPal subscription expired: workspace=%s", sub.workspace_id)

    elif event_type == "BILLING.SUBSCRIPTION.SUSPENDED":
        sub.status = "past_due"
        logger.warning("PayPal subscription suspended: workspace=%s", sub.workspace_id)

    elif event_type == "BILLING.SUBSCRIPTION.UPDATED":
        # Plan change — extract new plan info
        new_plan_id = resource.get("plan_id", "")
        # Map PayPal plan ID back to our plan name
        for plan_name in PLANS:
            if get_paypal_plan_id(plan_name) == new_plan_id:
                sub.plan = plan_name
                break
        logger.info("PayPal subscription updated: workspace=%s, plan=%s", sub.workspace_id, sub.plan)

    db.session.commit()


# ---------------------------------------------------------------------------
# Plan provisioning (create PayPal plans programmatically)
# ---------------------------------------------------------------------------

def setup_paypal_plans() -> dict[str, str]:
    """Create PayPal products/plans for each SpecForge tier.

    Returns a dict mapping plan_name -> paypal_plan_id.
    Call this once during initial setup.
    """
    access_token = _get_paypal_access_token()
    if not access_token:
        logger.error("Cannot setup PayPal plans: no access token")
        return {}

    plan_configs = {
        "pro": {
            "name": "SpecForge Pro",
            "description": "Professional plan with 100 analyses/month and AI enhancement.",
            "price": "19.99",
            "interval": "MONTH",
        },
        "enterprise": {
            "name": "SpecForge Enterprise",
            "description": "Unlimited analyses, priority queue, and team collaboration.",
            "price": "99.99",
            "interval": "MONTH",
        },
    }

    result = {}

    for plan_name, config in plan_configs.items():
        try:
            # Create product first
            product_resp = requests.post(
                _paypal_api_url("/v1/catalogs/products"),
                headers=_paypal_headers(access_token),
                json={
                    "name": config["name"],
                    "description": config["description"],
                    "type": "SERVICE",
                    "category": "SOFTWARE",
                },
                timeout=15,
            )
            product_resp.raise_for_status()
            product_id = product_resp.json().get("id")

            # Create billing plan
            plan_resp = requests.post(
                _paypal_api_url("/v1/billing/plans"),
                headers=_paypal_headers(access_token),
                json={
                    "product_id": product_id,
                    "name": config["name"],
                    "description": config["description"],
                    "status": "ACTIVE",
                    "billing_cycles": [
                        {
                            "frequency": {
                                "interval_unit": config["interval"],
                                "interval_count": 1,
                            },
                            "tenure_type": "REGULAR",
                            "sequence": 1,
                            "total_cycles": 0,  # Infinite
                            "pricing_scheme": {
                                "fixed_price": {
                                    "value": config["price"],
                                    "currency_code": "USD",
                                },
                            },
                        },
                    ],
                    "payment_preferences": {
                        "auto_bill_outstanding": True,
                        "payment_failure_threshold": 3,
                    },
                },
                timeout=15,
            )
            plan_resp.raise_for_status()
            paypal_plan_id = plan_resp.json().get("id")

            result[plan_name] = paypal_plan_id
            logger.info(
                "PayPal plan created: %s -> %s ($%s/%s)",
                plan_name,
                paypal_plan_id,
                config["price"],
                config["interval"],
            )

        except Exception as exc:
            logger.error("Failed to create PayPal plan for '%s': %s", plan_name, exc)

    return result
