import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.getcwd())


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    PORT = int(os.environ.get("PORT", 5000))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'specforge.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")
    TOKEN_ENCRYPTION_SECRET = os.environ.get("TOKEN_ENCRYPTION_SECRET", SECRET_KEY)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_BYTES", 65536))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_LIFETIME_HOURS", 12)))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    RATE_LIMITS = {
        "analyze": {"limit": int(os.environ.get("RATE_LIMIT_ANALYZE", 20)), "window": 60},
        "ai_chat": {"limit": int(os.environ.get("RATE_LIMIT_AI_CHAT", 10)), "window": 60},
        "ai_enhance": {"limit": int(os.environ.get("RATE_LIMIT_AI_ENHANCE", 10)), "window": 60},
        "auth_login": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_LOGIN", 10)), "window": 60},
        "auth_callback": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_CALLBACK", 20)), "window": 60},
        "list_analyses": {"limit": int(os.environ.get("RATE_LIMIT_LIST_ANALYSES", 60)), "window": 60},
        "get_analysis": {"limit": int(os.environ.get("RATE_LIMIT_GET_ANALYSIS", 120)), "window": 60},
        "get_job": {"limit": int(os.environ.get("RATE_LIMIT_GET_JOB", 120)), "window": 60},
        "auth_status": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_STATUS", 60)), "window": 60},
        "export_create": {"limit": int(os.environ.get("RATE_LIMIT_EXPORT_CREATE", 30)), "window": 60},
    }
    APP_VERSION = os.environ.get("APP_VERSION", "2.1.0")
    HEALTH_QUEUE_BACKLOG_WARNING = int(os.environ.get("HEALTH_QUEUE_BACKLOG_WARNING", 100))
    HEALTH_QUEUE_BACKLOG_CRITICAL = int(os.environ.get("HEALTH_QUEUE_BACKLOG_CRITICAL", 500))
    HEALTH_FAILED_JOBS_CRITICAL = int(os.environ.get("HEALTH_FAILED_JOBS_CRITICAL", 25))
    HEALTH_LIVENESS_VERSION = APP_VERSION

    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "")

    # Feature flags
    AI_ENHANCEMENT_ENABLED = os.environ.get("AI_ENHANCEMENT_ENABLED", "true").lower() == "true"
    EXPORT_SHARING_ENABLED = os.environ.get("EXPORT_SHARING_ENABLED", "true").lower() == "true"
    ANALYTICS_ENABLED = os.environ.get("ANALYTICS_ENABLED", "true").lower() == "true"
    QUOTA_ENFORCEMENT = os.environ.get("QUOTA_ENFORCEMENT", "strict")  # strict, soft, off
    JOB_STALE_MINUTES = int(os.environ.get("JOB_STALE_MINUTES", 15))
    JOB_STALE_CHECK_INTERVAL_SECONDS = int(os.environ.get("JOB_STALE_CHECK_INTERVAL_SECONDS", 300))
    # PayPal billing configuration
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_SANDBOX = os.environ.get("PAYPAL_SANDBOX", "true").lower() == "true"
    PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")
    # Plan IDs (set after creating plans in PayPal dashboard or via setup script)
    PAYPAL_PLAN_ID_PRO = os.environ.get("PAYPAL_PLAN_ID_PRO", "")
    PAYPAL_PLAN_ID_ENTERPRISE = os.environ.get("PAYPAL_PLAN_ID_ENTERPRISE", "")
    PAYPAL_PLAN_PRICE_PRO = os.environ.get("PAYPAL_PLAN_PRICE_PRO", "$19.99/month")
    PAYPAL_PLAN_PRICE_ENTERPRISE = os.environ.get("PAYPAL_PLAN_PRICE_ENTERPRISE", "$99.99/month")
