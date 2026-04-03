import logging

from flask import Flask, jsonify, request

from .config import Config
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.main import main_bp


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(config_class)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    register_error_handlers(app, logger)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    return app


def register_error_handlers(app, logger):
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not Found", "status": 404}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        logger.error("500: %s", request.path)
        return jsonify({"error": "Internal Server Error", "status": 500}), 500

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify({"error": "Bad Request", "status": 400}), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify({"error": "Forbidden", "status": 403}), 403

    @app.errorhandler(401)
    def unauthorized(_error):
        return jsonify({"error": "Unauthorized", "status": 401}), 401

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error("Unhandled: %s", str(error))
        return jsonify({"error": "Internal Server Error", "status": 500}), 500
