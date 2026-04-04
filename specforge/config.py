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
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_LIFETIME_HOURS", 12)))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    RATE_LIMITS = {
        "analyze": {"limit": int(os.environ.get("RATE_LIMIT_ANALYZE", 20)), "window": 60},
        "minimax_chat": {"limit": int(os.environ.get("RATE_LIMIT_MINIMAX_CHAT", 10)), "window": 60},
        "minimax_enhance": {"limit": int(os.environ.get("RATE_LIMIT_MINIMAX_ENHANCE", 10)), "window": 60},
        "minimax_login": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_LOGIN", 10)), "window": 60},
        "minimax_callback": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_CALLBACK", 20)), "window": 60},
        "list_analyses": {"limit": int(os.environ.get("RATE_LIMIT_LIST_ANALYSES", 60)), "window": 60},
        "get_analysis": {"limit": int(os.environ.get("RATE_LIMIT_GET_ANALYSIS", 120)), "window": 60},
        "get_job": {"limit": int(os.environ.get("RATE_LIMIT_GET_JOB", 120)), "window": 60},
        "minimax_status": {"limit": int(os.environ.get("RATE_LIMIT_AUTH_STATUS", 60)), "window": 60},
    }
    APP_VERSION = os.environ.get("APP_VERSION", "2.1.0")
    HEALTH_QUEUE_BACKLOG_WARNING = int(os.environ.get("HEALTH_QUEUE_BACKLOG_WARNING", 100))
    HEALTH_QUEUE_BACKLOG_CRITICAL = int(os.environ.get("HEALTH_QUEUE_BACKLOG_CRITICAL", 500))
    HEALTH_FAILED_JOBS_CRITICAL = int(os.environ.get("HEALTH_FAILED_JOBS_CRITICAL", 25))
    HEALTH_LIVENESS_VERSION = APP_VERSION

    MINIMAX_CLIENT_ID = os.environ.get("MINIMAX_CLIENT_ID", "")
    MINIMAX_CLIENT_SECRET = os.environ.get("MINIMAX_CLIENT_SECRET", "")
    MINIMAX_REDIRECT_URI = os.environ.get("MINIMAX_REDIRECT_URI", "")
    MINIMAX_AUTH_URL = "https://platform.minimaxi.com/oauth/authorize"
    MINIMAX_TOKEN_URL = "https://platform.minimaxi.com/oauth/token"
    MINIMAX_API_BASE = "https://api.minimaxi.com/v1"

    MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")
    MINIMAX_CHAT_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    MINIMAX_MODEL = "MiniMax-M2.5"
