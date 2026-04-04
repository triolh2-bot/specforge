# SpecForge Monitoring and Runbook

## Endpoints

- `GET /health/live` for process liveness and uptime.
- `GET /health/ready` for dependency-aware readiness across database, migrations, and job queue.
- `GET /health` as a compatibility alias that returns the same readiness posture.
- `GET /metrics` for counters and duration aggregates.

## Dashboard Coverage

Track these panels in the production dashboard:
- request volume and status classes from `/metrics`
- per-endpoint latency from `/metrics`
- completed and failed jobs from `/metrics`
- queued, running, and failed job counts from `/health/ready`
- readiness state for database, migrations, and queue from `/health/ready`

## Alert Thresholds

Alert when:
- `/health/ready` returns `503` for 2 consecutive minutes
- the `database` or `migrations` readiness checks move to `down`
- queued jobs reach `HEALTH_QUEUE_BACKLOG_CRITICAL`
- failed jobs reach `HEALTH_FAILED_JOBS_CRITICAL`
- 5xx responses stay above 5% for 5 minutes

## Runbook

1. Check `/health/ready` to identify whether the failure is database, migrations, or queue related.
2. Review `/metrics` for request spikes, latency regression, and failed job growth.
3. If queue pressure is the issue, drain traffic from the instance and inspect workers before re-enabling readiness.
4. If migrations are behind, roll forward the schema before restoring service.
5. If the database check is down, remove the instance from rotation and escalate to the data plane owner.
