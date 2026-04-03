import time

from flask import Blueprint, current_app, redirect, request, session, url_for

from ..http import error_response, json_response
from ..services.minimax import exchange_code_for_token, get_minimax_auth_url

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/minimax")
def minimax_login():
    if not current_app.config["MINIMAX_CLIENT_ID"]:
        return error_response(
            "MiniMax OAuth not configured. Set MINIMAX_CLIENT_ID environment variable.",
            status=400,
            code="oauth_not_configured",
        )

    auth_url = get_minimax_auth_url()
    return redirect(auth_url)


@auth_bp.route("/auth/minimax/callback")
def minimax_callback():
    error = request.args.get("error")
    if error:
        return error_response(error, status=400, code="oauth_error")

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return error_response("Missing authorization code", status=400, code="missing_field", details={"field": "code"})
    if state != session.get("oauth_state"):
        return error_response("Invalid state parameter", status=400, code="invalid_state")

    token_data = exchange_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        return error_response("Failed to obtain access token", status=400, code="token_exchange_failed")

    session["access_token"] = token_data["access_token"]
    session["refresh_token"] = token_data.get("refresh_token")
    session["token_expires_at"] = time.time() + token_data.get("expires_in", 3600)
    session["minimax_authenticated"] = True

    return redirect(url_for("main.index"))


@auth_bp.route("/auth/status")
def auth_status():
    is_authenticated = session.get("minimax_authenticated", False)
    token_expires = session.get("token_expires_at", 0)
    return json_response(
        {
            "authenticated": is_authenticated,
            "provider": "minimax" if is_authenticated else None,
            "token_expires_in": max(0, int(token_expires - time.time())) if is_authenticated else 0,
        }
    )


@auth_bp.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
