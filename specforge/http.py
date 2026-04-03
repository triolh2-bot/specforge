from uuid import uuid4

from flask import g, jsonify, request


def assign_request_id():
    request_id = request.headers.get("X-Request-ID", "").strip()
    g.request_id = request_id or str(uuid4())


def attach_request_id(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    return response


def json_response(payload, status=200):
    body = dict(payload)
    body.setdefault("request_id", getattr(g, "request_id", ""))
    return jsonify(body), status


def error_response(message, status=400, code="bad_request", details=None):
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": getattr(g, "request_id", ""),
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status
