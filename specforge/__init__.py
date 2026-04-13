import logging
import time

from flask import Flask, request

from .config import Config
from .extensions import db
from .http import assign_request_id, attach_request_id, error_response
from .routes.admin import admin_bp
from .routes.analytics import analytics_bp
from .routes.analyses import analyses_bp
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.billing import billing_bp
from .routes.exports import exports_bp
from .routes.jobs import jobs_bp
from .routes.legal import legal_bp
from .routes.main import main_bp
from .routes.members import members_bp
from .routes.metrics import metrics_bp
from .services.abuse import assign_rate_limit_client_id, enforce_content_length
from .services.ai_providers import register_builtin_providers, registry
from .services.migrations import run_migrations
from .services.observability import after_request_observer, before_request_observer, configure_logging
from .services.prompt_manager import register_builtin_templates
from .services.rbac import AuthorizationError
from .validation import ValidationError


def _csrf_origin_check():
    """Block cross-origin state-mutating requests (CSRF mitigation).

    Checks the Origin or Referer header against the server's own host.
    Only applies to POST, PUT, PATCH, DELETE — safe methods are skipped.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None

    origin = request.headers.get("Origin") or ""
    referer = request.headers.get("Referer") or ""
    server_host = request.host  # e.g. "localhost:5000" or "specforge.dev"

    # Allow if Origin matches
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.netloc == server_host:
            return None
    # Fall back to Referer
    elif referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        if parsed.netloc == server_host:
            return None

    # If neither header is present (e.g. same-origin form post from some browsers),
    # allow it — browsers always send at least one for cross-origin requests.
    if not origin and not referer:
        return None

    return error_response("Cross-origin request blocked", status=403, code="csrf_rejected")


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(config_class)
    app.extensions["started_at"] = time.time()

    configure_logging(app)
    logger = logging.getLogger(__name__)

    try:
        db.init_app(app)
        # Reset and re-register providers for each app instance (test isolation)
        registry.reset()
        register_builtin_providers()
        register_builtin_templates()
        app.before_request(assign_request_id)
        app.before_request(before_request_observer)
        app.before_request(assign_rate_limit_client_id)
        app.before_request(enforce_content_length)
        app.before_request(_csrf_origin_check)
        app.after_request(attach_request_id)
        app.after_request(after_request_observer)
        register_error_handlers(app, logger)
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(analyses_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(analytics_bp)
        app.register_blueprint(billing_bp)
        app.register_blueprint(exports_bp)
        app.register_blueprint(jobs_bp)
        app.register_blueprint(legal_bp)
        app.register_blueprint(members_bp)
        app.register_blueprint(metrics_bp)
        
        # Run migrations with error handling - don't fail app startup if DB isn't ready
        try:
            run_migrations(app)
        except Exception as migration_error:
            logger.error("Migration failed during startup (will retry lazily): %s", migration_error, exc_info=True)
            # Store migration error to retry lazily via before_request
            app.extensions["migration_pending"] = True
            app.extensions["migration_error"] = str(migration_error)
            
            # Add lazy migration retry hook
            @app.before_request
            def retry_migrations_if_pending():
                if app.extensions.get("migration_pending"):
                    try:
                        logger.info("Retrying pending migrations...")
                        run_migrations(app)
                        app.extensions["migration_pending"] = False
                        app.extensions.pop("migration_error", None)
                        logger.info("Migrations completed successfully")
                    except Exception as retry_error:
                        logger.error("Lazy migration retry failed: %s", retry_error)
                        # Don't block requests - migrations will retry on next request

        if app.config.get("QUOTA_ENFORCEMENT") == "off":
            logger.warning("Quota enforcement is OFF — do not use in production.")

        return app
    except Exception as e:
        logger.critical("Failed to create app: %s", str(e), exc_info=True)
        raise


def register_error_handlers(app, logger):
    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error):
        return error_response(
            str(error),
            status=403,
            code="forbidden",
            details={
                "permission": error.permission,
                "required_role": error.required_role,
                "actual_role": error.actual_role,
            },
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return error_response(
            error.message,
            status=error.status_code,
            code=error.code,
            details=error.details,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return error_response("Not Found", status=404, code="not_found")

    @app.errorhandler(500)
    def internal_error(_error):
        logger.error("500: %s", request.path)
        return error_response("Internal Server Error", status=500, code="internal_server_error")

    @app.errorhandler(400)
    def bad_request(_error):
        return error_response("Bad Request", status=400, code="bad_request")

    @app.errorhandler(403)
    def forbidden(_error):
        return error_response("Forbidden", status=403, code="forbidden")

    @app.errorhandler(401)
    def unauthorized(_error):
        return error_response("Unauthorized", status=401, code="unauthorized")

    @app.errorhandler(413)
    def payload_too_large(_error):
        return error_response("Request body is too large", status=413, code="payload_too_large")

    @app.errorhandler(429)
    def rate_limited(_error):
        return error_response("Rate limit exceeded", status=429, code="rate_limit_exceeded")

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error("Unhandled exception: %s", str(error), exc_info=True)
        # In debug mode, include the actual error message for easier debugging
        if app.debug:
            import traceback
            error_detail = f"{str(error)}\n\n{traceback.format_exc()}"
            return error_response(error_detail, status=500, code="internal_server_error")
        return error_response("Internal Server Error", status=500, code="internal_server_error")
