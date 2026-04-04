from flask import Blueprint, current_app, redirect, request, session, url_for

from ..http import error_response, json_response
from ..services.abuse import rate_limit
from ..services.auth_session import (
    clear_minimax_tokens,
    get_minimax_auth_status,
    rotate_auth_session,
    store_minimax_tokens,
)
from ..services.minimax import exchange_code_for_token, get_minimax_auth_url

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/minimax")
@rate_limit("minimax_login")
def minimax_login():
    if not current_app.config["MINIMAX_CLIENT_ID"]:
        return error_response(
            "MiniMax OAuth not configured. Set MINIMAX_CLIENT_ID environment variable.",
            status=400,
            code="oauth_not_configured",
        )

    rotate_auth_session()
    auth_url = get_minimax_auth_url()
    return redirect(auth_url)


@auth_bp.route("/auth/minimax/callback")
@rate_limit("minimax_callback")
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

    rotate_auth_session()
    store_minimax_tokens(
        token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 3600),
    )

    return redirect(url_for("main.index"))


@auth_bp.route("/auth/status")
@rate_limit("minimax_status")
def auth_status():
    auth_state = get_minimax_auth_status()
    return json_response(
        {
            "authenticated": auth_state["authenticated"],
            "provider": "minimax" if auth_state["authenticated"] else None,
            "token_expires_in": auth_state["token_expires_in"],
            "workspace_id": auth_state["workspace_id"],
            "role": auth_state["role"],
        }
    )


@auth_bp.route("/auth/logout")
def logout():
    clear_minimax_tokens()
    return redirect(url_for("main.index"))
