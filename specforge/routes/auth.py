from flask import Blueprint, current_app, redirect, request, session, url_for

from ..http import error_response, json_response
from ..services.abuse import rate_limit
from ..services.auth_session import (
    get_auth_status,
    rotate_auth_session,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/status")
@rate_limit("auth_status")
def auth_status():
    auth_state = get_auth_status()
    # authenticated will now refer to a valid session
    return json_response(
        {
            "authenticated": auth_state["authenticated"],
            "provider": None,
            "token_expires_in": 0,
            "workspace_id": auth_state["workspace_id"],
            "role": auth_state["role"],
        }
    )


@auth_bp.route("/auth/logout")
def logout():
    # session.clear() or specific logic if needed
    session.clear()
    return redirect(url_for("main.index"))
