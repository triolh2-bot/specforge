import time

from flask import Blueprint, jsonify, redirect, request, session, url_for, current_app

from ..services.minimax import exchange_code_for_token, get_minimax_auth_url

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/minimax")
def minimax_login():
    if not current_app.config["MINIMAX_CLIENT_ID"]:
        return jsonify(
            {
                "success": False,
                "error": "MiniMax OAuth not configured. Set MINIMAX_CLIENT_ID environment variable.",
            }
        ), 400

    auth_url = get_minimax_auth_url()
    return redirect(auth_url)


@auth_bp.route("/auth/minimax/callback")
def minimax_callback():
    error = request.args.get("error")
    if error:
        return jsonify({"success": False, "error": error}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("oauth_state"):
        return jsonify({"success": False, "error": "Invalid state parameter"}), 400

    token_data = exchange_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        return jsonify({"success": False, "error": "Failed to obtain access token"}), 400

    session["access_token"] = token_data["access_token"]
    session["refresh_token"] = token_data.get("refresh_token")
    session["token_expires_at"] = time.time() + token_data.get("expires_in", 3600)
    session["minimax_authenticated"] = True

    return redirect(url_for("main.index"))


@auth_bp.route("/auth/status")
def auth_status():
    is_authenticated = session.get("minimax_authenticated", False)
    token_expires = session.get("token_expires_at", 0)
    return jsonify(
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
