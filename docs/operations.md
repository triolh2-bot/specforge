# Operations

## Health Endpoints

- `GET /health/live` checks whether the web process is responding.
- `GET /health/ready` checks the database, job queue state, and OpenRouter provider configuration.
- `GET /health` is a compatibility alias that returns the readiness view with the same request-id envelope.

## Recommended Dashboards

- Uptime and HTTP status mix for `/health`, `/health/live`, `/health/ready`, `/analyze`, and `/api/jobs/*`.
- Queue backlog panel showing `queued_jobs`, `running_jobs`, and oldest queued job age.
- Provider error rate panel for OpenRouter authentication, rate limit, and API request failures.
- Latency percentiles for `analyze`, analysis fetch, job fetch, and auth endpoints.
- Rate-limit pressure panel for 429 responses by endpoint.

## Alert Thresholds

- Page on `/health/ready` returning 503 for more than 2 consecutive checks.
- Page when queued jobs exceed `HEALTH_QUEUE_BACKLOG_CRITICAL`.
- Warn when queued jobs exceed `HEALTH_QUEUE_BACKLOG_WARNING` for more than 10 minutes.
- Warn on sustained OpenRouter configuration failures or provider request errors.
- Warn when p95 latency for `/analyze` crosses the product SLO.

## Incident Runbook

1. Check `/health/ready` and identify the failing dependency in `checks`.
2. If the database is down, verify the database host, credentials, and migration state.
3. If queue backlog is elevated, inspect running jobs and worker capacity before scaling web traffic.
4. If provider status is degraded, confirm the OpenRouter API key, selected model, and site URL configuration.
5. If the issue is isolated to one endpoint, review structured logs by `request_id` and `workspace_id`.
6. After mitigation, confirm `/health/live`, `/health/ready`, and `/metrics` all recover.

## Deployment Notes

- Keep `HEALTH_QUEUE_BACKLOG_WARNING` and `HEALTH_QUEUE_BACKLOG_CRITICAL` aligned with expected worker throughput.
- Set `APP_VERSION` in the deployment environment so health payloads carry an explicit release identifier.
- Preserve `X-Request-ID` across proxies and load balancers so incidents can be correlated quickly.
