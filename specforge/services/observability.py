import json
import logging
import threading
import time
from collections import defaultdict

from flask import current_app, g, request, session


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "path"):
            payload["path"] = record.path
        if hasattr(record, "method"):
            payload["method"] = record.method
        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "workspace_id"):
            payload["workspace_id"] = record.workspace_id
        if hasattr(record, "auth_session_id"):
            payload["auth_session_id"] = record.auth_session_id
        if hasattr(record, "job_id"):
            payload["job_id"] = record.job_id
        if hasattr(record, "analysis_id"):
            payload["analysis_id"] = record.analysis_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class InMemoryMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._durations = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "max_ms": 0.0})

    def increment(self, name, value=1):
        with self._lock:
            self._counters[name] += value

    def observe(self, name, duration_ms):
        with self._lock:
            bucket = self._durations[name]
            bucket["count"] += 1
            bucket["total_ms"] += duration_ms
            bucket["max_ms"] = max(bucket["max_ms"], duration_ms)

    def snapshot(self):
        with self._lock:
            durations = {}
            for name, bucket in self._durations.items():
                avg_ms = bucket["total_ms"] / bucket["count"] if bucket["count"] else 0.0
                durations[name] = {
                    "count": bucket["count"],
                    "total_ms": round(bucket["total_ms"], 2),
                    "avg_ms": round(avg_ms, 2),
                    "max_ms": round(bucket["max_ms"], 2),
                }
            return {
                "counters": dict(self._counters),
                "durations": durations,
            }


def get_metrics():
    metrics = current_app.extensions.get("metrics")
    if metrics is None:
        metrics = InMemoryMetrics()
        current_app.extensions["metrics"] = metrics
    return metrics


def configure_logging(app):
    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers: remove all existing, add exactly one JSON handler.
    json_handler = None
    for handler in list(root_logger.handlers):
        if isinstance(handler.formatter, JsonFormatter):
            json_handler = handler
        else:
            root_logger.removeHandler(handler)

    if json_handler is None:
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(json_handler)

    # Prevent Flask's logger from double-emitting through the root logger
    app.logger.handlers = []
    app.logger.propagate = True
    app.logger.setLevel(level)


def before_request_observer():
    g.request_started_at = time.perf_counter()


def after_request_observer(response):
    started_at = getattr(g, "request_started_at", None)
    if started_at is None:
        return response

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    endpoint = request.endpoint or "unknown"
    metrics = get_metrics()
    metrics.increment("http_requests_total")
    metrics.increment(f"http_status_{response.status_code}")
    metrics.observe(f"http_request_duration_ms:{endpoint}", duration_ms)

    logging.getLogger("specforge.request").info(
        "request_completed",
        extra={
            "event": "http_request",
            "request_id": getattr(g, "request_id", ""),
            "path": request.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "workspace_id": session.get("workspace_id"),
            "auth_session_id": session.get("auth_session_id"),
        },
    )
    return response


def record_job_metric(event, duration_ms=None, job_id=None, analysis_id=None):
    logger = logging.getLogger("specforge.jobs")
    metrics = current_app.extensions.get("metrics")
    if metrics:
        metrics.increment(f"jobs_{event}_total")
        if duration_ms is not None:
            metrics.observe("job_duration_ms", duration_ms)

    logger.info(
        event,
        extra={
            "event": "job_lifecycle",
            "request_id": "",
            "job_id": job_id,
            "analysis_id": analysis_id,
            "duration_ms": duration_ms,
        },
    )
