import threading
import time
from collections import defaultdict, deque
from functools import wraps
import secrets

from flask import current_app, request, session

from ..http import error_response


class InMemoryRateLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, limit, window_seconds):
        now = time.time()
        threshold = now - window_seconds
        with self._lock:
            entries = self._events[key]
            while entries and entries[0] <= threshold:
                entries.popleft()
            if len(entries) >= limit:
                retry_after = max(1, int(entries[0] + window_seconds - now))
                return False, retry_after
            entries.append(now)
        return True, None


class RedisRateLimiter:
    def __init__(self, redis_url):
        import redis
        self.redis = redis.from_url(redis_url)

    def allow(self, key, limit, window_seconds):
        try:
            # Atomic rate limiting using Lua script
            script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
            local count = redis.call('ZCARD', key)
            
            if count >= limit then
                local first = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local retry_after = 1
                if #first > 0 then
                    retry_after = math.max(1, math.ceil(tonumber(first[2]) + window - now))
                end
                return {0, retry_after}
            end
            
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window)
            return {1, 0}
            """
            now = time.time()
            res = self.redis.eval(script, 1, key, limit, window_seconds, now)
            return bool(res[0]), res[1]
        except Exception as e:
            # Fallback to allowing request if Redis fails (fail-open for availability)
            current_app.logger.error(f"Redis rate limiter error: {e}")
            return True, None


def get_rate_limiter():
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        redis_url = current_app.config.get("REDIS_URL")
        if redis_url:
            try:
                limiter = RedisRateLimiter(redis_url)
                current_app.logger.info("Using RedisRateLimiter")
            except Exception as e:
                current_app.logger.error(f"Failed to initialize RedisRateLimiter: {e}")
                limiter = InMemoryRateLimiter()
        else:
            limiter = InMemoryRateLimiter()
            current_app.logger.info("Using InMemoryRateLimiter")
        current_app.extensions["rate_limiter"] = limiter
    return limiter


def assign_rate_limit_client_id():
    client_id = session.get("_rate_limit_client_id")
    if not client_id:
        session["_rate_limit_client_id"] = secrets.token_urlsafe(16)


def build_rate_limit_subject():
    client_id = session.get("_rate_limit_client_id")
    if client_id:
        return f"client:{client_id}"
    auth_session_id = session.get("auth_session_id")
    if auth_session_id:
        return f"session:{auth_session_id}"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    return f"ip:{request.remote_addr or 'unknown'}"


def rate_limit(limit_name):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            config = current_app.config.get("RATE_LIMITS", {})
            rule = config.get(limit_name)
            if not rule:
                return func(*args, **kwargs)

            limiter = get_rate_limiter()
            subject = build_rate_limit_subject()
            allowed, retry_after = limiter.allow(
                key=f"{limit_name}:{subject}",
                limit=rule["limit"],
                window_seconds=rule["window"],
            )
            if not allowed:
                response, status = error_response(
                    "Rate limit exceeded",
                    status=429,
                    code="rate_limit_exceeded",
                    details={"limit": rule["limit"], "window_seconds": rule["window"]},
                )
                response.headers["Retry-After"] = str(retry_after)
                return response, status
            return func(*args, **kwargs)

        return wrapped

    return decorator


def enforce_content_length():
    content_length = request.content_length
    max_length = current_app.config.get("MAX_CONTENT_LENGTH")
    if content_length is not None and max_length is not None and content_length > max_length:
        response, status = error_response(
            "Request body is too large",
            status=413,
            code="payload_too_large",
            details={"max_content_length": max_length},
        )
        return response, status
    return None
